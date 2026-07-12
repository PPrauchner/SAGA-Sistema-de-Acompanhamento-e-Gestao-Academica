"""
Repositório concreto para operações na coleção raiz departments/.

Responsabilidades:
- Herdar FirebaseRepository e especializar operações para a coleção departments/.
- has_programs(department_id): verifica se algum documento em programs/ referencia o
  departamento (departamento_id), usado para bloquear a exclusão de um departamento
  com programas vinculados (ADR-0004).
- get_nome_by_programa(programa_id): resolve o nome do departamento a partir de um
  programa (programa_id -> programs.departamento_id -> departments.nome), usado para
  derivar o departamento de orientadores/discentes em vez de armazená-lo por pessoa
  (issue #249).
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

    async def get_nome_by_programa(self, programa_id: str | None) -> str | None:
        """Resolve o nome do departamento-pai de um programa.

        Args:
            programa_id: Identificador do documento em programs/, ou None (ex: papel
                `adm`, que não pertence a programa algum).

        Returns:
            O `nome` do departamento vinculado ao programa, ou None se `programa_id`
            for None, o programa não existir, não tiver `departamento_id`, ou o
            departamento referenciado não existir.
        """
        if programa_id is None:
            return None
        program = await self._programs.get(programa_id)
        if program is None:
            return None
        department_id = program.get("departamento_id")
        if not department_id:
            return None
        department = await self.get(department_id)
        return department.get("nome") if department else None
