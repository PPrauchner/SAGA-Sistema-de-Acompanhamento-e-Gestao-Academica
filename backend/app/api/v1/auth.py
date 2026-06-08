"""
Router FastAPI para os endpoints de autenticação e gestão de convites.

Responsabilidades:
- POST /api/v1/auth/invite: coordenação cria convite de primeiro acesso gerando UUID token,
  persistindo em invites/{token} com TTL de 48h. Protegido por @requires_role('coordenacao')
  e @audit_operation.
- POST /api/v1/auth/first-access: usuário convidado define senha e ativa conta via Firebase
  Admin SDK (create_user + set_custom_user_claims). Cria documento users/{uid} no Firestore.
  Protegido por @audit_operation.
- GET /api/v1/auth/me: retorna perfil do usuário autenticado (uid, email, nome, role,
  programa_id, student_id ou advisor_id conforme papel). Protegido por @requires_role para
  todos os papéis.
- GET /api/v1/health: health check público — verifica disponibilidade da API e do Firebase.
"""

from fastapi import APIRouter

from backend.app.core.config import settings
from backend.app.core.firebase import is_initialized

router = APIRouter()


@router.get("/health", tags=["health"])
async def health_check() -> dict:
    """Health check público — verifica se a API e o Firebase estão acessíveis."""
    return {
        "status": "ok",
        "firebase": "connected" if is_initialized() else "error",
        "version": settings.api_version,
    }
