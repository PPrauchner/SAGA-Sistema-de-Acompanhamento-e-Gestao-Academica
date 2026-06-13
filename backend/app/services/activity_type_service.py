"""
Serviço de negócio para tipos de atividade creditável.

Responsabilidades:
- create_type(): cria novo tipo. Decorado com @requires_role('coordenacao') e @audit_operation.
- update_type(): atualiza campos de um tipo. Aciona @track_history (A03).
- toggle_active(): ativa/desativa um tipo. Aciona @track_history (A03).
- list_types(): lista todos os tipos do programa.
"""

from __future__ import annotations

from typing import Any

from backend.app.aspects.audit import audit_operation
from backend.app.aspects.authorization import requires_role
from backend.app.aspects.history import track_history
from backend.app.core.auth import CurrentUser
from backend.app.models.activity import ActivityTypeCreate, ActivityTypeUpdate
from backend.app.repositories.activity_repository import ActivityRepository


class ActivityTypeService:
    """Service responsável pelo CRUD de TipoAtividadeCreditavel."""

    def __init__(self) -> None:
        self._repo = ActivityRepository()

    async def list_types(self, only_active: bool = False) -> list[dict[str, Any]]:
        """Lista tipos de atividade creditável.

        Args:
            only_active: Se True, retorna apenas tipos ativos.

        Returns:
            Lista de dicts dos tipos de atividade.
        """
        return await self._repo.list_activity_types(only_active=only_active)

    @requires_role("coordenacao")
    @audit_operation
    async def create_type(
        self,
        body: ActivityTypeCreate,
        current_user: CurrentUser,
    ) -> dict[str, Any]:
        """Cria um novo tipo de atividade creditável.

        Args:
            body: Dados do novo tipo.
            current_user: Usuário autenticado (coordenação).

        Returns:
            Dict do tipo criado com id.
        """
        return await self._repo.create_activity_type(body.model_dump())

    @requires_role("coordenacao")
    @audit_operation
    @track_history(collection="activity_types", id_kwarg="type_id")
    async def update_type(
        self,
        type_id: str,
        body: ActivityTypeUpdate,
        current_user: CurrentUser,
    ) -> dict[str, Any]:
        """Atualiza campos de um tipo de atividade.

        Aciona aspecto A03 (@track_history) para versionar a alteração.

        Args:
            type_id: ID do tipo de atividade.
            body: Campos a atualizar.
            current_user: Usuário autenticado (coordenação).

        Returns:
            Dict atualizado.
        """
        updates = {k: v for k, v in body.model_dump().items() if v is not None}
        return await self._repo.update_activity_type(type_id, updates)

    @requires_role("coordenacao")
    @audit_operation
    @track_history(collection="activity_types", id_kwarg="type_id")
    async def toggle_active(
        self,
        type_id: str,
        current_user: CurrentUser,
    ) -> dict[str, Any]:
        """Ativa ou desativa um tipo de atividade.

        Aciona aspecto A03 (@track_history) pois mudança em 'ativo' afeta o fato
        tipo_ativo do motor lógico.

        Args:
            type_id: ID do tipo de atividade.
            current_user: Usuário autenticado (coordenação).

        Returns:
            Dict com o novo estado do tipo.
        """
        return await self._repo.toggle_activity_type(type_id)
