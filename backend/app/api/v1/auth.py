"""
Router FastAPI para os endpoints de autenticação e gestão de convites.

Responsabilidades:
- POST /api/v1/auth/invite: coordenação cria convite de primeiro acesso gerando UUID token,
  persistindo em invites/{token} com TTL de 48h. Protegido por @requires_role('coordenacao')
  e auditado por @audit_operation (A02).
- POST /api/v1/auth/first-access: usuário convidado define senha e ativa conta via Firebase
  Admin SDK (create_user + set_custom_user_claims). Cria documento users/{uid} no Firestore.
  Público — não requer JWT; auditado por @audit_operation (A02).
- GET /api/v1/auth/me: retorna perfil do usuário autenticado (uid, email, nome, role,
  programa_id, student_id ou advisor_id conforme papel). Protegido por @requires_role para
  todos os papéis.
- GET /api/v1/health: health check público — verifica disponibilidade da API e do Firebase.
"""

from fastapi import APIRouter, Depends, status

from backend.app.aspects.audit import audit_operation
from backend.app.aspects.authorization import requires_role
from backend.app.core.auth import CurrentUser, get_current_user
from backend.app.core.config import settings
from backend.app.core.firebase import is_initialized
from backend.app.models.user import (
    FirstAccessRequest,
    FirstAccessResponse,
    InviteRequest,
    InviteResponse,
    UserResponse,
)
from backend.app.services.auth_service import AuthService

router = APIRouter()


@router.post("/auth/invite", status_code=status.HTTP_201_CREATED)
@requires_role("coordenacao")
@audit_operation
async def create_invite(
    body: InviteRequest,
    user: CurrentUser = Depends(get_current_user),
) -> InviteResponse:
    """Coordenação cria um convite de primeiro acesso para um novo usuário."""
    return await AuthService().create_invite(body, user)


@router.post("/auth/first-access")
@audit_operation
async def first_access(body: FirstAccessRequest) -> FirstAccessResponse:
    """Endpoint público: usuário convidado define a senha e ativa a conta."""
    return await AuthService().activate_first_access(body.token, body.senha)


@router.get("/auth/me")
@requires_role("aluno", "orientador", "coordenacao")
async def get_me(
    user: CurrentUser = Depends(get_current_user),
) -> UserResponse:
    """Retorna o perfil do usuário autenticado atual."""
    return await AuthService().get_me(user)


@router.get("/health", tags=["health"])
async def health_check() -> dict:
    """Health check público — verifica se a API e o Firebase estão acessíveis."""
    return {
        "status": "ok",
        "firebase": "connected" if is_initialized() else "error",
        "version": settings.api_version,
    }
