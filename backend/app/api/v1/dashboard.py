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
- GET /api/v1/dashboard/orientador/{advisor_id}/indice: índice de produção do orientador
  autenticado + posição relativa anônima no programa. Exclusivo do próprio orientador via
  @requires_role('orientador') + @requires_ownership. (US-AN03)

Nota de segurança:
- Verificação de ownership dos dashboards existentes é delegada ao aspecto AOP
  `check_dashboard_ownership`.
- O endpoint /indice usa @requires_ownership diretamente (ownership simples:
  advisor_id == current_user.uid não se aplica — advisor_id é o doc-id em advisors/,
  não o uid; a barreira é feita via check_dashboard_ownership que já cobre este caso).
- Dashboard endpoints NÃO levam @audit_operation (somente @requires_role).
"""

from fastapi import APIRouter, Depends, Query

from backend.app.aspects.authorization import requires_role
from backend.app.aspects.ownership import check_dashboard_ownership
from backend.app.core.auth import CurrentUser, get_current_user
from backend.app.models.dashboard import (
    AlunoDashboardResponse,
    CoordDashboardResponse,
    DashboardIndiceOrientadorResponse,
    IndiceModalidade,
    OrientadorDashboardResponse,
)
from backend.app.services.dashboard_service import DashboardService

router = APIRouter()


def get_dashboard_service() -> DashboardService:
    return DashboardService()


@router.get("/dashboard/aluno/me", response_model=AlunoDashboardResponse)
@requires_role("aluno")
async def get_meu_aluno_dashboard(
    user: CurrentUser = Depends(get_current_user),
    service: DashboardService = Depends(get_dashboard_service),
) -> AlunoDashboardResponse:
    """Dashboard do discente autenticado.

    O student_id e derivado do CurrentUser.uid no backend; o frontend nao informa
    id de aluno e, portanto, nao consegue consultar dados de outro discente por
    este endpoint.
    """
    return await service.get_meu_aluno_dashboard(user)


@router.get("/dashboard/aluno/{student_id}", response_model=AlunoDashboardResponse)
@requires_role("aluno", "orientador", "coordenacao")
@check_dashboard_ownership()
async def get_aluno_dashboard(
    student_id: str,
    user: CurrentUser = Depends(get_current_user),
    service: DashboardService = Depends(get_dashboard_service),
) -> AlunoDashboardResponse:
    """Dashboard do aluno: situação, créditos, produções, tarefas pendentes.

    A verificação de ownership (aluno só vê o próprio, orientador só vê
    orientandos) é feita via aspecto AOP `check_dashboard_ownership`.
    """
    return await service.get_aluno_dashboard(student_id)


@router.get(
    "/dashboard/orientador/{advisor_id}",
    response_model=OrientadorDashboardResponse,
)
@requires_role("orientador", "coordenacao")
@check_dashboard_ownership()
async def get_orientador_dashboard(
    advisor_id: str,
    user: CurrentUser = Depends(get_current_user),
    service: DashboardService = Depends(get_dashboard_service),
) -> OrientadorDashboardResponse:
    """Dashboard do orientador: orientandos, status, atividades aguardando parecer."""
    return await service.get_orientador_dashboard(advisor_id)


@router.get("/dashboard/coordenacao", response_model=CoordDashboardResponse)
@requires_role("coordenacao")
async def get_coordenacao_dashboard(
    user: CurrentUser = Depends(get_current_user),
    service: DashboardService = Depends(get_dashboard_service),
) -> CoordDashboardResponse:
    """Dashboard da coordenação: visão macro do programa."""
    return await service.get_coordenacao_dashboard()


@router.get(
    "/dashboard/orientador/{advisor_id}/indice",
    response_model=DashboardIndiceOrientadorResponse,
)
@requires_role("orientador")
@check_dashboard_ownership()
async def get_dashboard_indice_orientador(
    advisor_id: str,
    modalidade: IndiceModalidade = Query(
        ...,
        description="Modalidade de cálculo: 'soma_total' ou 'media_por_orientando'",
    ),
    user: CurrentUser = Depends(get_current_user),
    service: DashboardService = Depends(get_dashboard_service),
) -> DashboardIndiceOrientadorResponse:
    """Índice de Produção do orientador + posição relativa anônima no programa.

    - `soma_total`: volume absoluto da bancada (soma das pontuações aprovadas).
    - `media_por_orientando`: produtividade normalizada (soma / nº orientandos).

    Anonimato Restrito: a resposta contém apenas estatísticas agregadas do
    programa. Nenhum UID, nome ou índice individual de colega é exposto.

    O parâmetro `modalidade` é obrigatório — retorna 422 se omitido.
    """
    return await service.get_dashboard_indice_orientador(advisor_id, modalidade)