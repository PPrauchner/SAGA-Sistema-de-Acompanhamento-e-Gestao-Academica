"""
Router FastAPI para gestão de usuários privilegiados.

Responsabilidades:
- POST /api/v1/users/coordenadores: adm cria um coordenador diretamente.
  Protegido por @requires_role('adm') — coordenacao e demais papéis recebem 403.

Referência: issue #162 (US-PA05); docs/specs/04_autenticacao.json.
"""

from fastapi import APIRouter, Depends, status

from backend.app.aspects.audit import audit_operation
from backend.app.aspects.authorization import requires_role
from backend.app.core.auth import CurrentUser, get_current_user
from backend.app.models.user import CreateCoordinatorRequest, CreateCoordinatorResponse
from backend.app.services.user_service import UserService

router = APIRouter()


@router.post("/users/coordenadores", status_code=status.HTTP_201_CREATED)
@requires_role("adm")
@audit_operation
async def create_coordinator(
    body: CreateCoordinatorRequest,
    user: CurrentUser = Depends(get_current_user),
) -> CreateCoordinatorResponse:
    """Adm cria um novo coordenador no sistema."""
    return await UserService().create_coordinator(body)
