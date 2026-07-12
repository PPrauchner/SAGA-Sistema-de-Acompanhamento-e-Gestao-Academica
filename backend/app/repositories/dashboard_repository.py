"""
Repository de Dashboard — consultas de leitura agregadora.

Responsabilidades:
- Encapsular acesso a coleções necessárias aos dashboards.
- Usar os repositórios atuais do projeto, com campos vigentes (`uid`,
  `orientador_id`, `programa_id`).
- Não expor dados individuais de outros orientadores no índice relativo.
"""

from __future__ import annotations

from typing import Any

from backend.app.repositories.activity_repository import ActivityRepository
from backend.app.repositories.advisor_repository import AdvisorRepository
from backend.app.repositories.production_repository import ProductionRepository
from backend.app.repositories.student_repository import StudentRepository

_TERMINAL_STUDENT_STATUSES = {"concluido", "desligado"}


class DashboardRepository:
    """Acesso a dados usados pelos dashboards e índices agregados."""

    def __init__(
        self,
        *,
        students: StudentRepository | None = None,
        advisors: AdvisorRepository | None = None,
        activities: ActivityRepository | None = None,
        productions: ProductionRepository | None = None,
    ) -> None:
        self._students = students or StudentRepository()
        self._advisors = advisors or AdvisorRepository()
        self._activities = activities or ActivityRepository()
        self._productions = productions or ProductionRepository()

    async def get_advisor(self, advisor_id: str) -> dict[str, Any] | None:
        """Retorna o orientador pelo id do documento advisors/{advisor_id}."""
        return await self._advisors.get(advisor_id)

    async def get_advisor_id_by_uid(self, uid: str) -> str | None:
        """Resolve o id interno do orientador a partir do uid autenticado."""
        advisors = await self._advisors.query(filters=[("uid", "==", uid)], limit=1)
        return advisors[0]["id"] if advisors else None

    async def list_active_students_by_advisor(self, advisor_id: str) -> list[dict[str, Any]]:
        """Lista orientandos ativos de um orientador usando query por orientador_id."""
        students = await self._students.query(filters=[("orientador_id", "==", advisor_id)])
        return [
            student
            for student in students
            if student.get("situacao_registrada") not in _TERMINAL_STUDENT_STATUSES
        ]

    async def list_advisors_by_program(self, programa_id: str | None) -> list[dict[str, Any]]:
        """Lista orientadores do mesmo programa do orientador avaliado."""
        if programa_id:
            return await self._advisors.query(filters=[("programa_id", "==", programa_id)])
        return await self._advisors.list_all()

    async def sum_approved_production_score_for_student(self, student_id: str) -> float:
        """Soma pontuação de produções aprovadas creditadas ao aluno."""
        activities = await self._activities.list_by_student(student_id)
        production_ids = {
            activity["producao_id"]
            for activity in activities
            if activity.get("status") == "aprovado" and activity.get("producao_id")
        }
        if not production_ids:
            return 0.0

        productions = await self._productions.list_by_ids(production_ids)
        return sum(
            float(production.get("pontuacao_calculada", 0.0) or 0.0)
            for production in productions
        )

    async def production_index_for_advisor(self, advisor_id: str, *, average: bool) -> tuple[float, int, float]:
        """Calcula índice, total de orientandos e pontuação total de um orientador."""
        students = await self.list_active_students_by_advisor(advisor_id)
        total_score = 0.0
        for student in students:
            total_score += await self.sum_approved_production_score_for_student(student["id"])

        total_students = len(students)
        index = (total_score / total_students) if average and total_students > 0 else total_score
        return round(index, 2), total_students, round(total_score, 2)
