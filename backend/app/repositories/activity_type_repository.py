"""
Repositório para tipos de atividades acadêmicas.

Responsabilidades:
- Implementar operações CRUD para a coleção 'activity_types'.
- Filtrar tipos de atividades por programa.
- Herdar FirebaseRepository e especializar operações.
"""

from typing import Any, Dict, List, Optional
from backend.app.repositories.firebase_repository import FirebaseRepository


class ActivityTypeRepository(FirebaseRepository):
    """Repositório concreto para tipos de atividades no Firestore."""

    def __init__(self):
        """Inicializa o ActivityTypeRepository."""
        super().__init__("activity_types")

    async def get_all_by_program(self, programa_id: str) -> List[Dict[str, Any]]:
        """Busca todos os tipos de atividades pertencentes a um programa específico.

        Args:
            programa_id: O identificador único do programa.

        Returns:
            Uma lista de documentos de tipos de atividades.
        """
        return await self.query(filters=[("programa_id", "==", programa_id)])

    async def get_type(self, type_id: str) -> Optional[Dict[str, Any]]:
        """Busca um único tipo de atividade por ID.

        Args:
            type_id: O identificador único do tipo de atividade.

        Returns:
            Os dados do tipo de atividade ou None.
        """
        return await self.get(type_id)

    async def create_type(self, data: Dict[str, Any]) -> str:
        """Cria um novo tipo de atividade.

        Args:
            data: Os dados do tipo de atividade.

        Returns:
            O ID do documento criado.
        """
        return await self.create(data)

    async def update_type(self, type_id: str, data: Dict[str, Any]) -> bool:
        """Atualiza um tipo de atividade existente.

        Args:
            type_id: O identificador único do tipo de atividade.
            data: Os campos para atualizar.

        Returns:
            True se a atualização for bem-sucedida.
        """
        return await self.update(type_id, data)
