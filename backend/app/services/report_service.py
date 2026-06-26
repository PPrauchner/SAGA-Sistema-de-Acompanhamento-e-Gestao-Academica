"""
Serviço de negócio para geração de relatórios gerenciais da coordenação.

Responsabilidades:
- get_students_at_risk(): alunos com situacao_inferida == 'em_risco', com as razões do risco
  lidas do último snapshot persistido em students/{id}/inferred_status/ (RL03).
- get_students_by_status(): contagem e lista resumida de alunos agrupados por
  situacao_registrada.
- get_students_by_advisor(): orientandos agrupados por orientador com distribuição de status.
- get_completion_time_avg(): média, mínimo e máximo de (data_conclusao - data_ingresso) para
  alunos com situacao_registrada == 'concluido'.
- get_productions_report(): produção bibliográfica creditada por aluno (via
  activities.producao_id aprovadas) e agregada por orientador, com distribuição por nível.
- Todos os métodos trabalham exclusivamente com dados persistidos no Firestore — não
  executam o motor de inferência em tempo real (a situação inferida já está cacheada em
  students/{id}.situacao_inferida pelo InferenceService).
"""

from __future__ import annotations

import asyncio
from datetime import date, datetime
from typing import Any

from fastapi import HTTPException, status

from backend.app.models.report import (
    AdvisorGroupItem,
    CompletionTimeItem,
    CompletionTimeResponse,
    ProductionByAdvisorItem,
    ProductionByStudentItem,
    ProductionLevelBreakdown,
    ProductionsReportResponse,
    StatusGroup,
    StudentAtRiskItem,
    StudentsAtRiskResponse,
    StudentsByAdvisorResponse,
    StudentsByStatusResponse,
    StudentStatusSummary,
)
from backend.app.repositories.activity_repository import ActivityRepository
from backend.app.repositories.advisor_repository import AdvisorRepository
from backend.app.repositories.production_repository import ProductionRepository
from backend.app.repositories.student_repository import StudentRepository

# Dias médios por mês (365.25 / 12) para converter duração em meses de integralização.
_DIAS_POR_MES = 30.44

# Níveis Qualis Único contabilizados no relatório de produção (por_nivel).
_NIVEIS_RELEVANCIA = ("A1", "A2", "A3", "A4", "B1", "B2", "SC")


def _to_date(value: Any) -> date | None:
    """Converte Timestamp Firestore (datetime), date ou string ISO em date, ou None."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value)[:10])
    except (ValueError, TypeError):
        return None


def _dias_restantes(prazo_final: Any) -> int | None:
    """Dias entre hoje e o prazo final do aluno (negativo se já expirou), ou None."""
    prazo = _to_date(prazo_final)
    if prazo is None:
        return None
    return (prazo - date.today()).days


class ReportService:
    """Agrega dados persistidos do Firestore nos cinco relatórios da coordenação."""

    def __init__(
        self,
        students: StudentRepository | None = None,
        advisors: AdvisorRepository | None = None,
        productions: ProductionRepository | None = None,
        activities: ActivityRepository | None = None,
    ) -> None:
        self._students = students or StudentRepository()
        self._advisors = advisors or AdvisorRepository()
        self._productions = productions or ProductionRepository()
        self._activities = activities or ActivityRepository()

    @staticmethod
    def _scope_to_own_student(
        students: list[dict[str, Any]], uid: str
    ) -> list[dict[str, Any]]:
        """Restringe a lista ao registro de discente do próprio solicitante (US-AN06).

        Args:
            students: Alunos já filtrados pelo programa do solicitante.
            uid: uid do discente solicitante.

        Returns:
            Lista contendo apenas o próprio aluno.

        Raises:
            HTTPException: 403 se o solicitante não tiver registro de discente no
                programa — acesso fora do escopo.
        """
        own = [student for student in students if student.get("uid") == uid]
        if not own:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Acesso negado: discente sem registro no programa",
            )
        return own

    async def _advisor_names(self) -> dict[str, str]:
        """Mapa orientador_id → nome para enriquecer os relatórios."""
        advisors = await self._advisors.list_all()
        return {advisor["id"]: advisor.get("nome", "") for advisor in advisors}

    async def get_students_at_risk(self) -> StudentsAtRiskResponse:
        """Lista alunos com situacao_inferida 'em_risco' e as razões do último snapshot."""
        students = await self._students.list_all()
        advisor_names = await self._advisor_names()

        at_risk = [s for s in students if s.get("situacao_inferida") == "em_risco"]
        razoes = await asyncio.gather(
            *[self._latest_risk_reasons(student["id"]) for student in at_risk]
        )

        items = [
            StudentAtRiskItem(
                student_id=student["id"],
                nome=student.get("nome", ""),
                orientador_nome=advisor_names.get(student.get("orientador_id"), ""),
                situacao_inferida=student.get("situacao_inferida", ""),
                dias_restantes_prazo=_dias_restantes(student.get("prazo_final")),
                razoes_risco=motivos,
            )
            for student, motivos in zip(at_risk, razoes)
        ]
        return StudentsAtRiskResponse(total=len(items), items=items)

    async def _latest_risk_reasons(self, student_id: str) -> list[str]:
        """Razões de risco do snapshot inferred_status mais recente do aluno."""
        snapshots = await self._students.list_subcollection(student_id, "inferred_status")
        if not snapshots:
            return []
        latest = max(snapshots, key=lambda snap: snap.get("timestamp", ""))
        return list(latest.get("riscos_detectados", []))

    async def get_students_by_status(self) -> StudentsByStatusResponse:
        """Agrupa alunos por situacao_registrada com total e lista resumida."""
        students = await self._students.list_all()
        advisor_names = await self._advisor_names()

        por_situacao: dict[str, StatusGroup] = {}
        for student in students:
            situacao = student.get("situacao_registrada")
            if situacao is None:
                continue
            resumo = StudentStatusSummary(
                student_id=student["id"],
                nome=student.get("nome", ""),
                orientador_nome=advisor_names.get(student.get("orientador_id"), ""),
                nivel=student.get("nivel", ""),
            )
            grupo = por_situacao.get(situacao)
            if grupo is None:
                por_situacao[situacao] = StatusGroup(total=1, alunos=[resumo])
            else:
                grupo.total += 1
                grupo.alunos.append(resumo)

        return StudentsByStatusResponse(por_situacao=por_situacao)

    async def get_students_by_advisor(self) -> StudentsByAdvisorResponse:
        """Agrupa orientandos por orientador com contagem de em_risco e regulares."""
        advisors = await self._advisors.list_all()
        students = await self._students.list_all()

        items = []
        for advisor in advisors:
            orientandos = [s for s in students if s.get("orientador_id") == advisor["id"]]
            items.append(
                AdvisorGroupItem(
                    advisor_id=advisor["id"],
                    advisor_nome=advisor.get("nome", ""),
                    total_orientandos=len(orientandos),
                    em_risco=sum(
                        1 for s in orientandos if s.get("situacao_registrada") == "em_risco"
                    ),
                    regulares=sum(
                        1 for s in orientandos if s.get("situacao_registrada") == "regular"
                    ),
                )
            )
        return StudentsByAdvisorResponse(items=items)

    async def get_completion_time_avg(self) -> CompletionTimeResponse:
        """Calcula média, mínimo e máximo do tempo de integralização dos concluídos.

        O tempo é a duração entre data_ingresso e data_conclusao; quando o aluno não tem
        data_conclusao explícita, usa-se atualizado_em (data da transição para 'concluido')
        como aproximação. Alunos concluídos sem nenhuma das datas ficam fora do histórico,
        mas continuam contados em total_concluidos.
        """
        students = await self._students.list_all()
        concluidos = [s for s in students if s.get("situacao_registrada") == "concluido"]

        historico = []
        for student in concluidos:
            ingresso = _to_date(student.get("data_ingresso"))
            conclusao = _to_date(student.get("data_conclusao")) or _to_date(
                student.get("atualizado_em")
            )
            if ingresso is None or conclusao is None:
                continue
            meses = round((conclusao - ingresso).days / _DIAS_POR_MES, 1)
            historico.append(
                CompletionTimeItem(
                    student_nome=student.get("nome", ""),
                    meses=meses,
                    ano_conclusao=conclusao.year,
                )
            )

        valores = [item.meses for item in historico]
        return CompletionTimeResponse(
            media_meses=round(sum(valores) / len(valores), 1) if valores else None,
            total_concluidos=len(concluidos),
            minimo_meses=min(valores) if valores else None,
            maximo_meses=max(valores) if valores else None,
            historico=historico,
        )

    async def get_productions_report(
        self, programa_id: str, role: str, uid: str
    ) -> ProductionsReportResponse:
        """Agrega produção bibliográfica creditada por aluno (RL05) e por orientador.

        Args:
            programa_id: Programa do solicitante; restringe alunos e produções
                agregados ao tenant correspondente (escopo US-AN06).
            role: Papel do solicitante; define o escopo dos dados retornados —
                discente vê apenas o próprio registro (US-AN06).
            uid: uid do solicitante, usado para resolver o próprio registro de
                discente quando o papel é aluno.
        """
        students = [
            student
            for student in await self._students.list_all()
            if student.get("programa_id") == programa_id
        ]
        if role == "aluno":
            students = self._scope_to_own_student(students, uid)
        advisor_names = await self._advisor_names()
        productions = [
            producao
            for producao in await self._productions.list_productions()
            if producao.get("programa_id") == programa_id
        ]
        producao_por_id = {producao["id"]: producao for producao in productions}

        activities_por_aluno = await asyncio.gather(
            *[self._activities.list_by_student(student["id"]) for student in students]
        )

        por_aluno = []
        producoes_creditadas: set[str] = set()
        agg_orientador: dict[str, dict[str, float]] = {}

        for student, atividades in zip(students, activities_por_aluno):
            credit_ids = {
                atividade["producao_id"]
                for atividade in atividades
                if atividade.get("status") == "aprovado"
                and atividade.get("producao_id") in producao_por_id
            }
            niveis = {nivel: 0 for nivel in _NIVEIS_RELEVANCIA}
            pontuacao_total = 0.0
            for producao_id in credit_ids:
                producao = producao_por_id[producao_id]
                producoes_creditadas.add(producao_id)
                nivel = producao.get("nivel", "SC")
                if nivel in niveis:
                    niveis[nivel] += 1
                pontuacao_total += producao.get("pontuacao_calculada", 0.0)

            if credit_ids:
                por_aluno.append(
                    ProductionByStudentItem(
                        student_id=student["id"],
                        student_nome=student.get("nome", ""),
                        total=len(credit_ids),
                        pontuacao_total=round(pontuacao_total, 2),
                        por_nivel=ProductionLevelBreakdown(**niveis),
                    )
                )

            orientador_id = student.get("orientador_id")
            if orientador_id:
                acc = agg_orientador.setdefault(
                    orientador_id, {"orientandos": 0, "total": 0, "pontuacao": 0.0}
                )
                acc["orientandos"] += 1
                acc["total"] += len(credit_ids)
                acc["pontuacao"] += pontuacao_total

        # Discente vê apenas a própria produção; agregados por orientador são
        # benchmarking gerencial fora do seu escopo (US-AN06).
        por_orientador = [] if role == "aluno" else [
            ProductionByAdvisorItem(
                advisor_id=orientador_id,
                advisor_nome=advisor_names.get(orientador_id, ""),
                total=int(acc["total"]),
                pontuacao_total=round(acc["pontuacao"], 2),
                pontuacao_media_orientandos=(
                    round(acc["pontuacao"] / acc["orientandos"], 2)
                    if acc["orientandos"]
                    else 0.0
                ),
            )
            for orientador_id, acc in agg_orientador.items()
        ]

        return ProductionsReportResponse(
            total_producoes_aprovadas=len(producoes_creditadas),
            por_aluno=por_aluno,
            por_orientador=por_orientador,
        )
