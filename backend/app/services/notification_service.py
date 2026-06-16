"""
Serviço de negócio para notificações in-app (aspecto A05).

Responsabilidades:
- mark_as_read(): marca uma notificação como lida, garantindo que apenas o próprio
  destinatário possa fazê-lo (404 se inexistente, 403 se não for o dono).
- Não cria notificações — a escrita em notifications/ é exclusiva do aspecto
  @trigger_alerts. A listagem é feita diretamente no frontend via onSnapshot.
- A verificação de propriedade (destinatario_id == user.uid) acompanha o padrão já usado
  em StudentService.get_student, pois o aspecto @requires_role cobre apenas o papel.
"""

from __future__ import annotations

from fastapi import HTTPException, status

from backend.app.core.auth import CurrentUser
from backend.app.models.notification import MarkReadResponse
from backend.app.repositories.firebase_repository import FirebaseRepository


class NotificationService:
    """Serviço de negócio para marcação de notificações como lidas."""

    def __init__(self) -> None:
        self._repo = FirebaseRepository("notifications")

    async def mark_as_read(
        self,
        notification_id: str,
        user: CurrentUser,
    ) -> MarkReadResponse:
        notification = await self._repo.get(notification_id)

        if notification is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Notificação não encontrada",
            )

        if notification.get("destinatario_id") != user.uid:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Acesso negado à notificação",
            )

        await self._repo.update(notification_id, {"lida": True})

        return MarkReadResponse(
            id=notification_id,
            lida=True,
            message="Notificação marcada como lida",
        )
