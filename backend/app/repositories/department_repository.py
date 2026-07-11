"""
Repositório concreto para operações na coleção raiz departments/.

Responsabilidades:
- Herdar FirebaseRepository e especializar operações para a coleção departments/.
- has_programs(department_id): verifica se algum documento em programs/ referencia o
  departamento (departamento_id), usado para bloquear a exclusão de um departamento
  com programas vinculados (ADR-0004).
"""

from __future__ import annotations

from backend.app.repositories.firebase_repository import FirebaseRepository


class DepartmentRepository(FirebaseRepository):
    def __init__(self) -> None:
        super().__init__("departments")
        self._programs = FirebaseRepository("programs")

    async def has_programs(self, department_id: str) -> bool:
        """Verifica se existe algum programa vinculado ao departamento.

        Args:
            department_id: Identificador do documento em departments/.

        Returns:
            True se pelo menos um programs/ tem departamento_id == department_id.
        """
        matches = await self._programs.query(
            filters=[("departamento_id", "==", department_id)],
            limit=1,
        )
        return bool(matches)
