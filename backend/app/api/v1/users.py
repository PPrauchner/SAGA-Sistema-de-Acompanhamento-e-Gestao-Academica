"""
Router FastAPI para gestão de usuários privilegiados.

Responsabilidades:
- POST /api/v1/users/coordenadores: adm cria um coordenador diretamente.
  Protegido por @requires_role('adm') — coordenacao e demais papéis recebem 403.
- PUT /api/v1/users/profile: usuário autenticado edita o próprio nome. Auditado
  por A02 e versionado por A03. `departamento` não é mais editável — é derivado
  de `programa_id` (ADR-0004 / issue #249).

Referência: issues #162 (US-PA05), #195; docs/specs/04_autenticacao.json.
"""

from fastapi import APIRouter, Depends, status

from backend.app.aspects.audit import audit_operation
from backend.app.aspects.authorization import requires_role
from backend.app.aspects.history import track_history
from backend.app.core.auth import CurrentUser, get_current_user
from backend.app.models.user import (
    CreateCoordinatorRequest,
    CreateCoordinatorResponse,
    ProfileUpdateRequest,
    ProfileUpdateResponse,
)
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


@router.put("/users/profile")
@requires_role("aluno", "orientador", "coordenacao")
@audit_operation
@track_history
async def update_profile(
    body: ProfileUpdateRequest,
    user: CurrentUser = Depends(get_current_user),
) -> ProfileUpdateResponse:
    """Usuário autenticado edita o próprio perfil."""
    return await UserService().update_profile(body, user)
