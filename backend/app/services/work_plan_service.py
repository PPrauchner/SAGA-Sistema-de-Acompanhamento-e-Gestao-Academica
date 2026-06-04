"""
Serviço de negócio para gestão do plano de trabalho, etapas, tasks e atualizações de progresso.

Responsabilidades:
- create_plan(), update_plan(): CRUD do plano. update_plan decorado com @track_history.
- create_stage(), update_stage(): gerenciar etapas do plano.
- create_task(), update_task(), update_task_status(): gerenciar tasks de uma etapa.
  update_task_status() gera fato task_concluida(task_id, student_id) quando status='concluida'.
- add_progress_update(): aluno registra progresso em uma task. Decorado com @check_deadlines
  (verifica task.prazo) e @trigger_alerts (notifica orientador).
- recalculate_plan_progress(): recalcula progresso_percentual do plano com base no percentual
  médio das atualizações de progresso de todas as tasks não-concluídas.
- Verificar autoridade do orientador (somente acessa tasks de próprios orientandos).
"""
