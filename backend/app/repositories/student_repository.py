"""
Repositório concreto para operações na coleção students/ e suas sub-coleções.

Responsabilidades:
- Herdar FirebaseRepository e especializar operações para a coleção students/.
- get_student(student_id), create_student(data), update_student(student_id, data),
  delete_student(student_id): CRUD básico.
- get_students_by_advisor(advisor_id): filtra students por orientador_id.
- get_students_by_status(status): filtra students por situacao_registrada.
- get_history(student_id): lê sub-coleção students/{id}/history/.
- save_history_snapshot(student_id, snapshot): persiste snapshot do aspecto A03 em
  students/{id}/history/{auto_id}.
- save_inferred_status(student_id, result): persiste snapshot em
  students/{id}/inferred_status/{auto_id} e atualiza students/{id}.situacao_inferida.
"""

from __future__ import annotations

from typing import Any

from backend.app.repositories.firebase_repository import FirebaseRepository


class StudentRepository(FirebaseRepository):
    """Repositório específico da coleção students."""

    def __init__(self) -> None:
        super().__init__("students")

    async def save_history_snapshot(
        self,
        student_id: str,
        snapshot: dict[str, Any],
    ) -> str:
        return await self.set_subcollection_auto(student_id, "history", snapshot)
