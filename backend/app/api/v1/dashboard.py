"""
Router FastAPI para os endpoints de dashboard dos três perfis de usuário.

Responsabilidades:
- GET /api/v1/dashboard/aluno/{student_id}: dados do dashboard do aluno — situação atual,
  progresso do plano, créditos por grupo, resumo do checklist, tasks próximas, produções
  aprovadas e atividades pendentes de validação. Aplica @requires_role para aluno (próprio),
  orientador e coordenação.
- GET /api/v1/dashboard/orientador/{advisor_id}: visão agregada dos orientandos do
  orientador — contagem por status, atividades aguardando parecer, lista de orientandos com
  alertas. Aplica @requires_role('orientador', 'coordenacao').
- GET /api/v1/dashboard/coordenacao: visão macro do programa — totais por status,
  atividades aguardando validação, prorrogações pendentes, produções do último mês, tempo
  médio de integralização e auditoria recente. Exclusivo de @requires_role('coordenacao').

Nota de segurança:
- Verificação de ownership (aluno só vê próprio dashboard, orientador só vê dashboards
  dos seus orientandos) é feita no DashboardService, não neste router.
- Dashboard endpoints NÃO levam @audit_operation (somente @requires_role).
"""

from fastapi import APIRouter, Depends

from backend.app.aspects.authorization import requires_role
from backend.app.core.auth import CurrentUser, get_current_user
from backend.app.models.dashboard import (
    AlunoDashboardResponse,
    CoordDashboardResponse,
    OrientadorDashboardResponse,
)
from backend.app.services.dashboard_service import DashboardService

router = APIRouter()

_service = DashboardService()


@router.get("/dashboard/aluno/{student_id}", response_model=AlunoDashboardResponse)
@requires_role("aluno", "orientador", "coordenacao")
async def get_aluno_dashboard(
    student_id: str,
    user: CurrentUser = Depends(get_current_user),
) -> AlunoDashboardResponse:
    """Dashboard do aluno: situação, créditos, produções, tarefas pendentes.

    A verificação de ownership (aluno só vê o próprio, orientador só vê
    orientandos) é feita internamente pelo DashboardService.
    """
    return await _service.get_aluno_dashboard(student_id)


@router.get(
    "/dashboard/orientador/{advisor_id}",
    response_model=OrientadorDashboardResponse,
)
@requires_role("orientador", "coordenacao")
async def get_orientador_dashboard(
    advisor_id: str,
    user: CurrentUser = Depends(get_current_user),
) -> OrientadorDashboardResponse:
    """Dashboard do orientador: orientandos, status, atividades aguardando parecer."""
    return await _service.get_orientador_dashboard(advisor_id)


@router.get("/dashboard/coordenacao", response_model=CoordDashboardResponse)
@requires_role("coordenacao")
async def get_coordenacao_dashboard(
    user: CurrentUser = Depends(get_current_user),
) -> CoordDashboardResponse:
    """Dashboard da coordenação: visão macro do programa."""
    return await _service.get_coordenacao_dashboard()
