"""
Modelos Pydantic de resposta para os três dashboards por papel.

Responsabilidades:
- AlunoDashboardResponse: situação atual, progresso do plano, créditos por grupo,
  resumo do checklist, tasks próximas, produções aprovadas, atividades pendentes.
- OrientadorDashboardResponse: visão agregada dos orientandos — contagem por status,
  atividades aguardando parecer, lista de orientandos com alertas.
- CoordDashboardResponse: visão macro do programa — totais por status, pendências,
  tempo médio de integralização, auditoria recente.
- Mapeia os contratos de GET /api/v1/dashboard/* definidos em
  docs/specs/09_relatorios_dashboard.json.
"""

from __future__ import annotations

from pydantic import BaseModel


class CreditosResumo(BaseModel):
    """Créditos do aluno por grupo de atividade."""

    total: float = 0.0
    basico: float = 0.0
    especifico: float = 0.0
    tecnologico: float = 0.0
    minimo_requerido: float = 24.0


class ChecklistResumo(BaseModel):
    """Resumo numérico do checklist de integralização (não executa o motor)."""

    cumpridos: int = 0
    pendentes: int = 0
    em_risco: int = 0
    total: int = 0


class TaskProxima(BaseModel):
    """Task do plano de trabalho próxima do prazo."""

    task_id: str
    titulo: str
    prazo: str
    status: str


class AlunoDashboardResponse(BaseModel):
    """Resposta de GET /api/v1/dashboard/aluno/{student_id}."""

    student_id: str
    nome: str
    situacao_registrada: str
    situacao_inferida: str
    conflito_situacao: bool
    prazo_final: str | None = None
    dias_restantes: int = 0
    progresso_plano_percentual: float = 0.0
    creditos: CreditosResumo = CreditosResumo()
    checklist_resumo: ChecklistResumo = ChecklistResumo()
    tasks_proximas: list[TaskProxima] = []
    producoes_aprovadas: int = 0
    atividades_pendentes_validacao: int = 0


class OrientandoResumo(BaseModel):
    """Resumo de um orientando na visão do orientador."""

    student_id: str
    nome: str
    situacao_inferida: str
    progresso_plano: float = 0.0
    dias_restantes_prazo: int = 0
    alertas: list[str] = []


class OrientandosPorStatus(BaseModel):
    """Contagem de orientandos por status."""

    regular: int = 0
    em_risco: int = 0
    qualificado: int = 0
    fase_defesa: int = 0
    em_prorrogacao: int = 0


class OrientadorDashboardResponse(BaseModel):
    """Resposta de GET /api/v1/dashboard/orientador/{advisor_id}."""

    advisor_id: str
    nome: str
    total_orientandos: int = 0
    orientandos_por_status: OrientandosPorStatus = OrientandosPorStatus()
    atividades_aguardando_parecer: int = 0
    orientandos: list[OrientandoResumo] = []


class AlunosPorStatus(BaseModel):
    """Contagem de alunos por status para a visão da coordenação."""

    regular: int = 0
    em_risco: int = 0
    em_prorrogacao: int = 0
    qualificado: int = 0
    fase_defesa: int = 0


class AuditoriaRecenteItem(BaseModel):
    """Item de auditoria recente no dashboard da coordenação."""

    operacao: str
    usuario: str
    timestamp: str


class CoordDashboardResponse(BaseModel):
    """Resposta de GET /api/v1/dashboard/coordenacao."""

    programa_id: str
    total_alunos_ativos: int = 0
    alunos_por_status: AlunosPorStatus = AlunosPorStatus()
    atividades_aguardando_validacao: int = 0
    prorrogacoes_pendentes: int = 0
    producoes_ultimo_mes: int = 0
    tempo_medio_integralizacao_meses: float | None = None
    auditoria_recente: list[AuditoriaRecenteItem] = []
