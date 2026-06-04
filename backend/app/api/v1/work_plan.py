"""
Router FastAPI para os endpoints de plano de trabalho, etapas, tasks e atualizações de progresso.

Responsabilidades:
- GET /api/v1/work-plan/{student_id}: retorna plano completo com etapas, tasks e últimas
  atualizações de progresso. Acessível por aluno (próprio), orientador (orientandos) e
  coordenação.
- POST /api/v1/work-plan/{student_id}: cria plano de trabalho do aluno.
  Aplica @requires_role('orientador') e @audit_operation.
- PUT /api/v1/work-plan/{plan_id}: atualiza dados gerais do plano.
  Aplica @requires_role('orientador'), @audit_operation e @track_history.
- POST /api/v1/work-plan/{plan_id}/stages: adiciona etapa ao plano.
- POST /api/v1/stages/{stage_id}/tasks: adiciona task a uma etapa.
- PATCH /api/v1/tasks/{task_id}/status: orientador atualiza status de task.
  Gera fato task_concluida para o motor quando status='concluida'.
- POST /api/v1/tasks/{task_id}/updates: aluno registra atualização de progresso.
  Aplica @check_deadlines (verifica task.prazo) e @trigger_alerts (notifica orientador).
- GET /api/v1/tasks/{task_id}/updates: lista atualizações de progresso de uma task.
"""
