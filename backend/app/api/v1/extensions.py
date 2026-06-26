"""Router FastAPI para solicitacoes de prorrogacao."""

from fastapi import APIRouter, Depends, status

from backend.app.aspects.audit import audit_operation
from backend.app.aspects.authorization import requires_role
from backend.app.core.auth import CurrentUser, get_current_user
from backend.app.models.extension import ExtensionCreateRequest, ExtensionResponse
from backend.app.services.extension_service import ExtensionService

router = APIRouter()

service = ExtensionService()


@router.get("/extensions", response_model=list[ExtensionResponse])
@requires_role("aluno", "orientador", "coordenacao")
async def list_extensions(
    user: CurrentUser = Depends(get_current_user),
) -> list[ExtensionResponse]:
    """Lista prorrogacoes visiveis para o usuario autenticado."""
    return await service.list_extensions(user)


@router.post(
    "/extensions",
    response_model=ExtensionResponse,
    status_code=status.HTTP_201_CREATED,
)
@requires_role("aluno", "orientador")
@audit_operation
async def create_extension(
    body: ExtensionCreateRequest,
    user: CurrentUser = Depends(get_current_user),
) -> ExtensionResponse:
    """Cria uma solicitacao de prorrogacao para aluno ou orientando."""
    return await service.create_extension(body, user)
