"""
Repositório da sub-coleção versionada de pesos Qualis de um programa.

Responsabilidades:
- create_version(programa_id, data): grava uma nova versão (auto-id) em
  programs/{programa_id}/qualis_weights/ — nunca sobrescreve versões anteriores.
- list_versions(programa_id): lê todas as versões do programa (o próprio histórico).

Restrição: sem lógica de negócio — apenas leitura e escrita. A resolução da versão vigente
por data é responsabilidade do QualisWeightsService.
"""

from __future__ import annotations

from typing import Any

from backend.app.repositories.firebase_repository import FirebaseRepository

_QUALIS_WEIGHTS_SUBCOLLECTION = "qualis_weights"


class QualisWeightsRepository(FirebaseRepository):
    """Repositório das versões de pesos Qualis aninhadas sob programs/."""

    def __init__(self) -> None:
        super().__init__("programs")

    async def create_version(self, programa_id: str, data: dict[str, Any]) -> str:
        """Grava uma nova versão de pesos (auto-id), preservando as anteriores.

        Args:
            programa_id: ID do documento em programs/.
            data: Conteúdo da versão (pesos + vigente_desde/alterado_por/alterado_em).

        Returns:
            ID gerado para o documento da versão.
        """
        return await self.set_subcollection_auto(
            programa_id, _QUALIS_WEIGHTS_SUBCOLLECTION, data
        )

    async def list_versions(self, programa_id: str) -> list[dict[str, Any]]:
        """Lista todas as versões de pesos do programa (histórico completo).

        Args:
            programa_id: ID do documento em programs/.

        Returns:
            Lista de versões, cada uma com o id do documento injetado.
        """
        return await self.list_subcollection(
            programa_id, _QUALIS_WEIGHTS_SUBCOLLECTION
        )
