"""
Serviço de negócio para gestão de tipos de atividade creditável.

Responsabilidades:
- Implementar a lógica de negócios para operações CRUD em tipos de atividades.
- Suportar a ativação/desativação do status ativo de tipos de atividades.
- Coordenar com ActivityTypeRepository para persistência de dados.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException, status

from backend.app.core.auth import CurrentUser
from backend.app.models.activity_type import ActivityTypeCreate, ActivityTypeToggleRequest, ActivityTypeUpdate
from backend.app.repositories.activity_type_repository import ActivityTypeRepository


class ActivityTypeService:
    """Serviço para lidar com a lógica de negócios de tipos de atividades."""

    def __init__(self, repository=None):
        """Inicializa o ActivityTypeService.

        Args:
            repository: Uma instância de ActivityTypeRepository. Se None, uma nova é criada.
        """
        self.repository = repository or ActivityTypeRepository()

    async def list_types(self) -> list[dict[str, Any]]:
        """Lista todos os tipos do programa (acessível a aluno, orientador e coordenação)."""
        return await self.repository.list_all()

    async def get_all_by_program(self, programa_id: str) -> list[dict[str, Any]]:
        """Busca todos os tipos de atividades pertencentes a um programa específico.

        Args:
            programa_id: O identificador único do programa.

        Returns:
            Uma lista de documentos de tipos de atividades.
        """
        return await self.repository.get_all_by_program(programa_id)

    async def create_type(
        self,
        data: ActivityTypeCreate,
        user: CurrentUser | None = None,
    ) -> str | dict:
        """Cria um novo tipo de atividade.

        Args:
            data: Os dados do tipo de atividade validados pelo Pydantic.
            user: O usuário atual, opcionalmente usado para registrar autoria.

        Returns:
            O ID do documento criado, ou um dicionário se `user` for fornecido.
        """
        now = datetime.now(timezone.utc)
        payload = data.model_dump()
        
        if user:
            payload.update({
                "programa_id": user.programa_id,
                "criado_por": user.uid,
                "criado_em": now,
                "atualizado_em": now,
                "ativo": True
            })

        type_id = await self.repository.create_type(payload)

        if user:
            return {
                "id": type_id,
                "nome": data.nome,
            }
        return type_id

    async def update_type(
        self,
        type_id: str,
        data: ActivityTypeUpdate,
        user: CurrentUser | None = None,
    ) -> bool | dict:
        """Atualiza um tipo de atividade existente.

        Args:
            type_id: O identificador único do tipo de atividade.
            data: Os dados de atualização validados pelo Pydantic.
            user: O usuário atual que realiza a operação.

        Returns:
            True se a atualização for bem-sucedida, ou dicionário se `user` for fornecido.
        """
        await self._get_or_404(type_id)

        update_dict = data.model_dump(exclude_unset=True, exclude_none=True, exclude={"observacao"})
        if update_dict:
            update_dict["atualizado_em"] = datetime.now(timezone.utc)
            await self.repository.update_type(type_id, update_dict)

        if user:
            return {
                "message": "Tipo atualizado",
                "historico_criado": True,
            }
        return True

    async def toggle_active(
        self,
        type_id: str,
        data: ActivityTypeToggleRequest | None = None,
        user: CurrentUser | None = None,
    ) -> bool | dict:
        """Ativa ou desativa o status de um tipo de atividade.

        Args:
            type_id: O identificador único do tipo de atividade.
            data: Dados opcionais da requisição (ex: observação, status).
            user: O usuário atual que realiza a operação.

        Returns:
            True se a alteração for bem-sucedida, ou dicionário se `user` for fornecido.
        """
        current_type = await self._get_or_404(type_id)
        
        new_status = data.ativo if data else not current_type.get("ativo", True)
        
        await self.repository.update_type(
            type_id,
            {"ativo": new_status, "atualizado_em": datetime.now(timezone.utc)},
        )

        if user:
            return {
                "message": "Tipo ativado" if new_status else "Tipo desativado",
                "historico_criado": True,
            }
        return True

    async def _get_or_404(self, type_id: str) -> dict:
        """Obtém o tipo de atividade ou lança erro 404.

        Args:
            type_id: O identificador único do tipo de atividade.

        Returns:
            O documento do tipo de atividade.
        """
        existing = await self.repository.get_type(type_id)

        if existing is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tipo de atividade não encontrado",
            )

        return existing
