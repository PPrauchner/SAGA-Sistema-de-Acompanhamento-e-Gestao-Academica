"""
Serviço de negócio para agregação de dados dos dashboards dos três perfis.

Responsabilidades:
- get_aluno_dashboard(student_id) -> AlunoDashboardResponse: agrega situação atual,
  progresso do plano, créditos por grupo, resumo do checklist, tasks próximas, produções
  aprovadas e atividades pendentes de validação. Exibe badge de conflito se
  situacao_registrada != situacao_inferida. Não executa o motor em tempo real — lê
  situacao_inferida já persistida pelo InferenceService.
- get_orientador_dashboard(advisor_id) -> OrientadorDashboardResponse: visão agregada dos
  orientandos — contagem por status, atividades aguardando parecer, lista de orientandos
  com progresso e alertas.
- get_coordenacao_dashboard() -> CoordDashboardResponse: visão macro do programa — totais
  por status, atividades aguardando validação, prorrogações pendentes, produções do último
  mês, tempo médio de integralização e auditoria recente.
"""

from __future__ import annotations

from datetime import date, datetime, timezone

from fastapi import HTTPException, status

from backend.app.core.auth import CurrentUser
from backend.app.models.dashboard import (
    AlunoDashboardResponse,
    AlunosPorStatus,
    AuditoriaRecenteItem,
    ChecklistResumo,
    CoordDashboardResponse,
    CreditosResumo,
    OrientadorDashboardResponse,
    OrientandoResumo,
    OrientandosPorStatus,
    TaskProxima,
)
from backend.app.repositories.activity_repository import ActivityRepository
from backend.app.repositories.activity_type_repository import ActivityTypeRepository
from backend.app.repositories.advisor_repository import AdvisorRepository
from backend.app.repositories.firebase_repository import FirebaseRepository
from backend.app.repositories.student_repository import StudentRepository
from backend.app.repositories.work_plan_repository import WorkPlanRepository




def _to_iso_date(value: object) -> str | None:
    """Converte datetime/date do Firestore para string ISO, ou None."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return str(value) or None


def _days_remaining(prazo_final: object) -> int:
    """Calcula dias restantes até o prazo final a partir de hoje."""
    if prazo_final is None:
        return 0
    if isinstance(prazo_final, datetime):
        target = prazo_final.date()
    elif isinstance(prazo_final, date):
        target = prazo_final
    else:
        return 0
    return (target - date.today()).days


def _aggregate_credits(activities: list[dict], types_map: dict[str, str]) -> CreditosResumo:
    """Soma créditos de atividades aprovadas por grupo de categoria."""
    basico = 0.0
    especifico = 0.0
    tecnologico = 0.0
    for act in activities:
        if act.get("status") != "aprovado":
            continue
        creditos = float(act.get("creditos_concedidos") or act.get("creditos_gerados") or 0.0)
        tipo_id = act.get("tipo_id", "")
        categoria = types_map.get(tipo_id, "")
        if categoria == "basico":
            basico += creditos
        elif categoria == "especifico":
            especifico += creditos
        elif categoria == "tecnologico":
            tecnologico += creditos
    return CreditosResumo(
        total=basico + especifico + tecnologico,
        basico=basico,
        especifico=especifico,
        tecnologico=tecnologico,
    )


_STATUS_FIELD_MAP: dict[str, str] = {
    "regular": "regular",
    "em_risco": "em_risco",
    "qualificado": "qualificado",
    "em_fase_de_defesa": "fase_defesa",
    "em_prorrogacao": "em_prorrogacao",
}
"""Mapeia valores de situacao_inferida no Firestore para atributos do modelo."""


def _count_by_status(
    students: list[dict],
) -> dict[str, int]:
    """Conta alunos por situacao_inferida, mapeando para nomes de atributo."""
    counts: dict[str, int] = {v: 0 for v in _STATUS_FIELD_MAP.values()}
    for s in students:
        sit = s.get("situacao_inferida", "")
        attr = _STATUS_FIELD_MAP.get(sit)
        if attr:
            counts[attr] += 1
    return counts


def _build_orientando_resumo(student: dict) -> OrientandoResumo:
    """Constrói resumo de um orientando para o dashboard do orientador."""
    alertas: list[str] = []
    sit = student.get("situacao_inferida", "")
    if sit == "em_risco":
        alertas.append("Situação em risco")
    dias = _days_remaining(student.get("prazo_final"))
    if 0 < dias <= 90:
        alertas.append(f"Prazo crítico: {dias} dias restantes")
    elif dias <= 0 and student.get("prazo_final") is not None:
        alertas.append("Prazo expirado")

    return OrientandoResumo(
        student_id=student.get("id", ""),
        nome=student.get("nome", ""),
        situacao_inferida=sit,
        progresso_plano=0.0,  # TODO: integrar com WorkPlanRepository
        dias_restantes_prazo=dias,
        alertas=alertas,
    )




class DashboardService:
    """Serviço de agregação de dados para os dashboards dos três perfis."""

    def __init__(self) -> None:
        self._students = StudentRepository()
        self._advisors = AdvisorRepository()
        self._activities = ActivityRepository()
        self._activity_types = ActivityTypeRepository()
        self._audit_logs = FirebaseRepository("audit_logs")
        self._extensions = FirebaseRepository("extensions")
        self._productions = FirebaseRepository("productions")
        self._work_plan = WorkPlanRepository()


    async def get_aluno_dashboard(self, student_id: str) -> AlunoDashboardResponse:
        """Agrega dados do dashboard do aluno a partir de dados persistidos.

        Não executa o motor de inferência — lê situacao_inferida já calculada.

        Args:
            student_id: ID do documento em students/.

        Returns:
            AlunoDashboardResponse com dados agregados.

        Raises:
            HTTPException(403): Se o usuário não tiver permissão.
            HTTPException(404): Se o aluno não existir.
        """
        student = await self._students.get(student_id)
        if student is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Aluno não encontrado",
            )

        situacao_reg = student.get("situacao_registrada", "")
        situacao_inf = student.get("situacao_inferida", "")

        activities = await self._activities.list_by_student(student_id)
        
        types_list = await self._activity_types.list_all()
        types_map = {t.get("id"): t.get("categoria", "") for t in types_list}
        creditos = _aggregate_credits(activities, types_map)
        
        producoes_aprovadas = sum(
            1
            for a in activities
            if a.get("status") == "aprovado" and a.get("producao_id")
        )
        atividades_pendentes = sum(
            1 for a in activities if a.get("status") == "enviado"
        )
        
        tasks = await self._work_plan.get_all_tasks_for_student(student_id)
        total_tasks = len(tasks)
        concluidas = sum(1 for t in tasks if t.get("concluida"))
        progresso = (concluidas / total_tasks * 100.0) if total_tasks > 0 else 0.0
        
        pendentes = [t for t in tasks if not t.get("concluida")]
        try:
            pendentes.sort(key=lambda x: str(x.get("prazo") or "9999-12-31"))
        except Exception:
            pass
            
        tasks_proximas_list = []
        for t in pendentes[:3]:
            tasks_proximas_list.append(TaskProxima(
                task_id=t.get("id", ""),
                titulo=t.get("titulo", "Tarefa sem título"),
                prazo=str(t.get("prazo") or "Sem prazo"),
                status="Pendente"
            ))

        checklist = ChecklistResumo(total=total_tasks, cumpridos=concluidas, pendentes=total_tasks - concluidas, em_risco=0)

        return AlunoDashboardResponse(
            student_id=student_id,
            nome=student.get("nome", ""),
            situacao_registrada=situacao_reg,
            situacao_inferida=situacao_inf,
            conflito_situacao=situacao_reg != situacao_inf,
            prazo_final=_to_iso_date(student.get("prazo_final")),
            dias_restantes=_days_remaining(student.get("prazo_final")),
            progresso_plano_percentual=progresso,
            creditos=creditos,
            checklist_resumo=checklist,
            tasks_proximas=tasks_proximas_list,
            producoes_aprovadas=producoes_aprovadas,
            atividades_pendentes_validacao=atividades_pendentes,
        )


    async def get_orientador_dashboard(
        self, advisor_id: str
    ) -> OrientadorDashboardResponse:
        """Agrega dados do dashboard do orientador.

        Lista orientandos, conta por status, soma atividades aguardando parecer.

        Args:
            advisor_id: ID do documento em advisors/.

        Returns:
            OrientadorDashboardResponse com dados agregados.

        Raises:
            HTTPException(403): Se não tiver permissão.
            HTTPException(404): Se o orientador não existir.
        """
        advisor = await self._advisors.get(advisor_id)
        if advisor is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Orientador não encontrado",
            )
        all_students = await self._students.list_all()
        orientandos = [
            s for s in all_students if s.get("orientador_id") == advisor_id
        ]
        status_counts = _count_by_status(orientandos)

        total_pending = 0
        for s in orientandos:
            activities = await self._activities.list_by_student(s.get("id", ""))
            total_pending += sum(
                1 for a in activities if a.get("status") == "enviado"
            )

        orientandos_resumo = []
        for s in orientandos:
            student_id = s.get("id", "")
            resumo = _build_orientando_resumo(s)
            
            # Fetch tasks and calculate progress
            tasks = await self._work_plan.get_all_tasks_for_student(student_id)
            total_tasks = len(tasks)
            concluidas = sum(1 for t in tasks if t.get("concluida"))
            resumo.progresso_plano = (concluidas / total_tasks * 100.0) if total_tasks > 0 else 0.0
            
            orientandos_resumo.append(resumo)

        return OrientadorDashboardResponse(
            advisor_id=advisor_id,
            nome=advisor.get("nome", ""),
            total_orientandos=len(orientandos),
            orientandos_por_status=OrientandosPorStatus(**status_counts),
            atividades_aguardando_parecer=total_pending,
            orientandos=orientandos_resumo,
        )

    async def get_coordenacao_dashboard(self) -> CoordDashboardResponse:
        """Agrega dados do dashboard da coordenação.

        Visão macro: totais por status, atividades aguardando validação,
        prorrogações pendentes, produções recentes, tempo médio, auditoria.

        Returns:
            CoordDashboardResponse com dados agregados.
        """
        all_students = await self._students.list_all()

        status_counts = _count_by_status(all_students)

        total_pending = 0
        for s in all_students:
            activities = await self._activities.list_by_student(s.get("id", ""))
            total_pending += sum(
                1 for a in activities if a.get("status") == "enviado"
            )

        tempo_medio = _compute_avg_completion_time(all_students)
        total_concluidos = sum(1 for s in all_students if s.get("situacao_registrada") == "concluido")
        total_alunos_ativos = sum(1 for s in all_students if s.get("situacao_registrada") not in ("concluido", "desligado"))
        audit_logs = await self._audit_logs.list_all()
        auditoria_recente = _build_recent_audit(audit_logs, limit=5)
        
        all_exts = await self._extensions.list_all()
        prorrogacoes_pendentes = sum(1 for e in all_exts if e.get("status") == "pendente")
        
        all_prods = await self._productions.list_all()
        import datetime
        thirty_days_ago = datetime.date.today() - datetime.timedelta(days=30)
        producoes_ultimo_mes = 0
        for p in all_prods:
            d = p.get("data")
            if d:
                if isinstance(d, datetime.datetime):
                    d = d.date()
                if isinstance(d, datetime.date) and d >= thirty_days_ago:
                    producoes_ultimo_mes += 1

        return CoordDashboardResponse(
            programa_id="prog_default",
            total_alunos=len(all_students),
            total_alunos_ativos=total_alunos_ativos,
            alunos_por_status=AlunosPorStatus(**status_counts),
            atividades_aguardando_validacao=total_pending,
            prorrogacoes_pendentes=prorrogacoes_pendentes,
            producoes_ultimo_mes=producoes_ultimo_mes,
            total_concluidos=total_concluidos,
            tempo_medio_integralizacao_meses=tempo_medio,
            auditoria_recente=auditoria_recente,
        )


def _compute_avg_completion_time(students: list[dict]) -> float | None:
    """Calcula média de integralização dos alunos com situacao_registrada=concluido."""
    durations: list[float] = []
    for s in students:
        if s.get("situacao_registrada") != "concluido":
            continue
        ingresso = s.get("data_ingresso")
        conclusao = s.get("data_conclusao") or s.get("prazo_final")
        if ingresso is None or conclusao is None:
            continue
        if isinstance(ingresso, datetime):
            ingresso = ingresso.date()
        if isinstance(conclusao, datetime):
            conclusao = conclusao.date()
        dias = (conclusao - ingresso).days
        if dias > 0:
            durations.append(dias / 30.0)
    return sum(durations) / len(durations) if durations else None


def _build_recent_audit(
    audit_logs: list[dict], *, limit: int = 5
) -> list[AuditoriaRecenteItem]:
    """Constrói lista de auditoria recente, ordenada do mais recente."""
    _min_ts = datetime.min.replace(tzinfo=timezone.utc)
    sorted_logs = sorted(
        audit_logs,
        key=lambda log: log.get("timestamp") or _min_ts,
        reverse=True,
    )
    result: list[AuditoriaRecenteItem] = []
    for log in sorted_logs[:limit]:
        ts = log.get("timestamp")
        ts_str = ""
        if isinstance(ts, datetime):
            ts_str = ts.isoformat()
        elif ts is not None:
            ts_str = str(ts)
        result.append(
            AuditoriaRecenteItem(
                operacao=log.get("operacao", ""),
                usuario=log.get("usuario_id", ""),
                timestamp=ts_str,
            )
        )
    return result
