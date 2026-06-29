"""
Repositório para configurações de programas acadêmicos e níveis de veículos.

Responsabilidades:
- Implementar operações CRUD para a coleção 'programs'.
- Gerenciar níveis de relevância de veículos como sub-coleções de um programa.
"""

import asyncio
from typing import Any
from backend.app.repositories.firebase_repository import FirebaseRepository
from backend.app.core.firebase import get_firestore_client


class ProgramRepository(FirebaseRepository):
    """Repositório concreto para dados relacionados a programas no Firestore."""

    def __init__(self):
        """Inicializa o ProgramRepository."""
        super().__init__("programs")

    async def list_programs(self) -> list[dict[str, Any]]:
        """Lista todos os programas cadastrados na coleção 'programs'.

        Returns:
            Uma lista de programas, cada um incluindo o campo `id` do documento.
        """
        return await self.list_all()

    async def get_config(self, programa_id: str) -> dict[str, Any] | None:
        """Busca a configuração de um determinado programa.

        Args:
            programa_id: O identificador único do programa.

        Returns:
            Os dados de configuração do programa ou None.
        """
        return await self.get(programa_id)

    async def update_config(self, programa_id: str, data: dict[str, Any]) -> bool:
        """Atualiza a configuração de um determinado programa.

        Args:
            programa_id: O identificador único do programa.
            data: Os campos a serem atualizados.

        Returns:
            True se a atualização foi bem-sucedida.
        """
        return await self.update(programa_id, data)

    async def get_vehicle_levels(self, programa_id: str) -> list[dict[str, Any]]:
        """Busca todos os níveis de relevância de veículos de um programa.

        Args:
            programa_id: O identificador único do programa.

        Returns:
            Uma lista de mapeamentos de níveis de veículos.
        """
        collection_path = f"{self.collection}/{programa_id}/vehicle_levels"
        return await self.query(subcollection_path=collection_path)

    async def update_vehicle_level(self, programa_id: str, veiculo_id: str, data: dict[str, Any]) -> bool:
        """Atualiza ou cria um mapeamento de nível de relevância de veículo.

        Args:
            programa_id: O identificador único do programa.
            veiculo_id: O identificador único do veículo.
            data: Os dados de nível e peso.

        Returns:
            True se a atualização foi bem-sucedida.
        """
        collection_path = f"{self.collection}/{programa_id}/vehicle_levels"
        
        def _update():
            get_firestore_client().collection(collection_path).document(veiculo_id).set(data, merge=True)
            return True
            
        return await asyncio.to_thread(_update)

