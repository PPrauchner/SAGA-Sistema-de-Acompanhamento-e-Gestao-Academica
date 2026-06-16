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

# Valores de situacao_registrada renomeados após o rename fase_defesa → em_fase_de_defesa.
# Documentos gravados antes do rename ainda carregam o valor legado; normalizamos na
# leitura para não quebrar consumidores (frontend e validação de StudentResponse).
_SITUACAO_LEGADA: dict[str, str] = {"fase_defesa": "em_fase_de_defesa"}


def _normalize_situacao_registrada(student: dict[str, Any]) -> dict[str, Any]:
    """Substitui in-place o valor legado de situacao_registrada pelo nome atual."""
    atual = _SITUACAO_LEGADA.get(student.get("situacao_registrada"))
    if atual is not None:
        student["situacao_registrada"] = atual
    return student


class StudentRepository(FirebaseRepository):
    """Repositório específico da coleção students."""

    def __init__(self) -> None:
        super().__init__("students")

    async def get(self, doc_id: str) -> dict[str, Any] | None:
        """Lê o aluno normalizando situacao_registrada legada (rename fase_defesa)."""
        student = await super().get(doc_id)
        return _normalize_situacao_registrada(student) if student is not None else None

    async def list_all(self) -> list[dict[str, Any]]:
        """Lista alunos normalizando situacao_registrada legada (rename fase_defesa)."""
        return [_normalize_situacao_registrada(student) for student in await super().list_all()]

    async def save_history_snapshot(
        self,
        student_id: str,
        snapshot: dict[str, Any],
    ) -> str:
        return await self.set_subcollection_auto(student_id, "history", snapshot)
