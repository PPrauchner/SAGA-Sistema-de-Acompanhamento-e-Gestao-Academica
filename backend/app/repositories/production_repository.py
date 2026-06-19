"""
Repositório concreto para a coleção raiz productions/.

Responsabilidades:
- create(data): cria documento de produção com auto-id na coleção raiz.
- get(production_id): lê uma produção por id (com o id injetado), ou None.

Restrição: sem lógica de negócio — apenas leitura e escrita. A produção é coleção raiz; o
vínculo com cada aluno autor vive em students/{id}/activities (activities.producao_id). A
pontuação RL05 e os níveis de veículo são resolvidos pelo ProductionService e pelo
InferenceRepository.
"""

from __future__ import annotations

from typing import Any

from backend.app.repositories.firebase_repository import FirebaseRepository


class ProductionRepository:
    """Repositório da coleção raiz productions/."""

    def __init__(self) -> None:
        self._productions = FirebaseRepository("productions")

    async def create(self, data: dict[str, Any]) -> str:
        """Cria uma produção na coleção raiz e retorna o id gerado."""
        return await self._productions.create(data)

    async def get(self, production_id: str) -> dict[str, Any] | None:
        """Lê uma produção por id (com o id injetado), ou None se não existir."""
        return await self._productions.get(production_id)
