"""
Router FastAPI para os endpoints de notificações in-app (aspecto A05).

Responsabilidades:
- PATCH /api/v1/notifications/{notification_id}/read: marca uma notificação como lida.
  Disponível a qualquer papel autenticado; a propriedade (apenas o destinatário) é validada
  no service. A leitura da lista é feita diretamente pelo frontend via onSnapshot, então
  não há endpoint de listagem aqui.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from backend.app.aspects.authorization import requires_role
from backend.app.core.auth import CurrentUser, get_current_user
from backend.app.models.notification import MarkReadResponse
from backend.app.services.notification_service import NotificationService

router = APIRouter()

service = NotificationService()


@router.patch("/notifications/{notification_id}/read")
@requires_role("aluno", "orientador", "coordenacao")
async def mark_notification_read(
    notification_id: str,
    user: CurrentUser = Depends(get_current_user),
) -> MarkReadResponse:
    return await service.mark_as_read(notification_id, user)
