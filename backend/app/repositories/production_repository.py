"""
Repositório concreto para a sub-coleção students/{id}/productions.

Responsabilidades:
- create(student_id, data): cria documento de produção com auto-id na sub-coleção.
- list_by_student(student_id): lista as produções de um aluno, incluindo o id de cada uma.

Restrição: sem lógica de negócio — apenas leitura e escrita. Pontuação RL05 e níveis de
veículo são resolvidos pelo ProductionService e pelo InferenceRepository.
"""

from __future__ import annotations

from typing import Any

from backend.app.repositories.firebase_repository import FirebaseRepository

_PRODUCTIONS_SUBCOLLECTION = "productions"


class ProductionRepository:
    """Repositório da sub-coleção productions de cada aluno."""

    def __init__(self) -> None:
        self._students = FirebaseRepository("students")

    async def create(self, student_id: str, data: dict[str, Any]) -> str:
        return await self._students.set_subcollection_auto(
            student_id, _PRODUCTIONS_SUBCOLLECTION, data
        )

    async def list_by_student(self, student_id: str) -> list[dict[str, Any]]:
        return await self._students.list_subcollection(
            student_id, _PRODUCTIONS_SUBCOLLECTION
        )
