"""
Repositório concreto para operações na coleção advisors/.

Responsabilidades:
- Herdar FirebaseRepository e especializar operações para a coleção advisors/.
- get_advisor(advisor_id), create_advisor(data), update_advisor(advisor_id, data),
  delete_advisor(advisor_id): CRUD básico.
- get_advisors_with_student_count(): lista orientadores enriquecidos com contagem de
  orientandos_ativos via query na coleção students/ filtrada por orientador_id e
  situacao_registrada não-terminal.
- check_advisor_capacity(advisor_id): verifica se orientador ainda está abaixo do
  limite_orientandos configurado.
"""

from __future__ import annotations

from backend.app.repositories.firebase_repository import FirebaseRepository
from backend.app.repositories.student_repository import StudentRepository

_TERMINAL_STUDENT_STATUSES = {"concluido", "desligado"}


class AdvisorRepository(FirebaseRepository):
    def __init__(self) -> None:
        super().__init__("advisors")

    async def get_advisors_with_student_count(
        self,
    ) -> list[dict]:

        advisors = await self.list_all()

        students = await StudentRepository().list_all()

        for advisor in advisors:
            advisor["orientandos_ativos"] = sum(
                1
                for student in students
                if student.get("orientador_id") == advisor["id"]
                and student.get("situacao_registrada") not in _TERMINAL_STUDENT_STATUSES
            )

        return advisors

    async def count_active_students(
        self,
        advisor_id: str,
    ) -> int:
        students = await StudentRepository().list_all()

        return sum(
            1
            for student in students
            if student.get("orientador_id") == advisor_id
            and student.get("situacao_registrada") not in _TERMINAL_STUDENT_STATUSES
        )

    async def check_advisor_capacity(
        self,
        advisor_id: str,
    ) -> bool:

        advisor = await self.get(advisor_id)

        if advisor is None:
            return False

        students = await StudentRepository().list_all()

        current = sum(
            1
            for student in students
            if student.get("orientador_id") == advisor_id
            and student.get("situacao_registrada") not in _TERMINAL_STUDENT_STATUSES
        )

        return current < advisor.get(
            "limite_orientandos",
            5,
        )
