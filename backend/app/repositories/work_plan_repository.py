"""
Repositório concreto para as sub-coleções do plano de trabalho no Firestore.

Responsabilidades:
- Acessar e persistir dados nas sub-coleções aninhadas de students/{id}/work_plan/:
  /stages/{stage_id}, /stages/{id}/tasks/{task_id}, /tasks/{id}/updates/{update_id}.
- Métodos: get_plan(student_id), create_plan(student_id, data), update_plan(plan_id, data).
- Métodos de etapa: create_stage(plan_id, data), list_stages(plan_id).
- Métodos de task: create_task(stage_id, data), update_task(task_id, data),
  list_tasks(stage_id), get_all_tasks_for_student(student_id).
- Métodos de progresso: create_update(task_id, data), list_updates(task_id).
- Calcular progresso_percentual do plano com base nas atualizações mais recentes das tasks.
"""
