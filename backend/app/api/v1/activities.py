"""
Router FastAPI para os endpoints de atividades creditáveis.

Responsabilidades:
- GET /api/v1/activities: lista atividades com filtros de student_id, status e categoria.
  Aluno vê as próprias; orientador vê dos orientandos; coordenação vê todas.
- POST /api/v1/activities: aluno registra nova atividade. Motor RL04 verifica elegibilidade
  preliminar imediatamente. Aplica @requires_role('aluno'), @audit_operation,
  @check_deadlines (verifica data_realizacao dentro do período do curso) e @trigger_alerts
  (notifica orientador após submissão).
- PATCH /api/v1/activities/{activity_id}/validate: orientador emite parecer ou coordenação
  aprova/rejeita. Operação mais crítica do fluxo — aplica @requires_role, @audit_operation
  e @trigger_alerts (notifica aluno após decisão). Motor verifica elegibilidade (RL04).
"""
