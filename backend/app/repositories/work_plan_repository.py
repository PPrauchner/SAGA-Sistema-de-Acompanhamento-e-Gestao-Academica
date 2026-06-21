"""
Repositório concreto para as sub-coleções do plano de trabalho no Firestore.

Responsabilidades:
- Acessar e persistir dados nas sub-coleções aninhadas de students/{id}/work_plan/:
  /stages/{stage_id}, /stages/{id}/tasks/{task_id}, /tasks/{id}/updates/{update_id}.
- Métodos: get_plan(student_id), create_plan(student_id, data), update_plan(plan_id, data).
- Métodos de etapa: create_stage(plan_id, data), list_stages(plan_id).
- Métodos de task: create_task(stage_id, data), update_task(task_id, data),
  list_tasks(stage_id), get_all_tasks_for_student(student_id).
- Calcular progresso_percentual do plano com base nas atualizações mais recentes das tasks.
"""

from __future__ import annotations

import asyncio
from typing import Any

from backend.app.core.firebase import get_firestore_client
from backend.app.repositories.firebase_repository import FirebaseRepository


class WorkPlanRepository(FirebaseRepository):
    """Acesso especializado ao plano de trabalho do aluno.
    A raiz deste repositório é a coleção 'students'.
    """

    def __init__(self) -> None:
        super().__init__("students")

    async def get_all_tasks_for_student(self, student_id: str) -> list[dict[str, Any]]:
        """Recupera todas as tasks do plano de trabalho de um aluno, iterando stages.
        """
        def _fetch_tasks() -> list[dict[str, Any]]:
            db = get_firestore_client()
            plans_ref = db.collection("students").document(student_id).collection("work_plan").stream()
            
            all_tasks = []
            
            for plan in plans_ref:
                stages_ref = plan.reference.collection("stages").stream()
                for stage in stages_ref:
                    tasks_ref = stage.reference.collection("tasks").stream()
                    for task in tasks_ref:
                        task_data = task.to_dict() or {}
                        task_data["id"] = task.id
                        task_data["stage_id"] = stage.id
                        all_tasks.append(task_data)
                        
            return all_tasks

        return await asyncio.to_thread(_fetch_tasks)
