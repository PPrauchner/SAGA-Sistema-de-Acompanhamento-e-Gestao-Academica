"""Router FastAPI para o endpoint unificado de solicitacoes."""

from fastapi import APIRouter, Depends

from backend.app.core.auth import CurrentUser, get_current_user
from backend.app.aspects.authorization import requires_role
from backend.app.models.request import RequestItem
from backend.app.services.request_service import RequestService

router = APIRouter()


@router.get(
    "/requests",
    response_model=list[RequestItem],
    summary="Listar solicitacoes pendentes",
)
@requires_role("aluno", "orientador", "coordenacao", "adm")
async def list_requests(
    user: CurrentUser = Depends(get_current_user),
    service: RequestService = Depends(RequestService),
) -> list[RequestItem]:
    """
    Retorna a lista unificada de solicitacoes pendentes de acao ou visualizacao,
    de acordo com o papel e escopo do usuario autenticado.
    - Aluno: ve suas solicitacoes pendentes criadas em outros fluxos.
    - Orientador: ve as atividades e prorrogacoes de seus orientandos que aguardam seu parecer,
      bem como as transferencias de coordenacao onde e o destino.
    - Coordenacao: ve as atividades, prorrogacoes e transferencias de orientando aguardando
      validacao/aprovacao final do seu programa.
    - ADM: ve todas as transferencias de coordenacao globais.
    """
    return await service.get_requests(user)
