"""
Serviço de negócio para gestão de tipos de atividade creditável.

Responsabilidades:
- Implementar CRUD de tipos de atividade delegando persistência ao ActivityTypeRepository.
- list_types(): lista todos os tipos do programa (acessível a aluno, orientador e
  coordenação).
- create_type(): cria novo tipo de atividade com status ativo=True por padrão.
- update_type(): atualiza pontuação, limite, flags. Aciona @track_history (histórico de
  TipoAtividadeCreditavel).
- toggle_active(): ativa ou desativa o tipo. Aciona @track_history.
- A01/A02/A03 são aplicados nos endpoints, conforme ordem canônica do projeto.
"""

from __future__ import annotations

from fastapi import HTTPException, status

from backend.app.core.auth import CurrentUser
from backend.app.models.activity_type import (
    ActivityTypeCreateRequest,
    ActivityTypeToggleRequest,
    ActivityTypeUpdateRequest,
)
from backend.app.repositories.activity_type_repository import ActivityTypeRepository


class ActivityTypeService:
    """Serviço de negócio para gestão de tipos de atividade creditável."""

    def __init__(self) -> None:
        self._types = ActivityTypeRepository()

    async def list_types(self) -> list[dict]:
        return await self._types.list_all()

    async def create_type(
        self,
        data: ActivityTypeCreateRequest,
        user: CurrentUser,
    ) -> dict:
        type_id = await self._types.create(
            {
                **data.model_dump(),
                "ativo": True,
            },
        )

        return {
            "id": type_id,
            "nome": data.nome,
        }

    async def update_type(
        self,
        type_id: str,
        data: ActivityTypeUpdateRequest,
        user: CurrentUser,
    ) -> dict:
        await self._get_or_404(type_id)

        fields = data.model_dump(exclude_none=True, exclude={"observacao"})
        if fields:
            await self._types.update(type_id, fields)

        return {
            "message": "Tipo atualizado",
            "historico_criado": True,
        }

    async def toggle_active(
        self,
        type_id: str,
        data: ActivityTypeToggleRequest,
        user: CurrentUser,
    ) -> dict:
        await self._get_or_404(type_id)

        await self._types.update(type_id, {"ativo": data.ativo})

        return {
            "message": "Tipo ativado" if data.ativo else "Tipo desativado",
            "historico_criado": True,
        }

    async def _get_or_404(self, type_id: str) -> dict:
        existing = await self._types.get(type_id)

        if existing is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tipo de atividade não encontrado",
            )

        return existing
