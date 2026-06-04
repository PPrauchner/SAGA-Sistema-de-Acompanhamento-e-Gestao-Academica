"""
Serviço de negócio para registro e validação de atividades creditáveis.

Responsabilidades:
- submit_activity(): aluno registra atividade. Executa motor RL04 via InferenceService para
  calcular elegibilidade_preliminar. Decorado com @requires_role('aluno'),
  @audit_operation, @check_deadlines e @trigger_alerts.
- advisor_review(): orientador emite parecer (sem aprovar). Decorado com
  @requires_role('orientador') e @audit_operation.
- validate_activity(): coordenação aprova ou rejeita atividade definitivamente.
  Atualiza creditos_gerados, status e gera fato producao_bibliografica_validada se aplicável.
  Decorado com @requires_role('coordenacao'), @audit_operation e @trigger_alerts.
- list_activities(): filtra atividades por student_id, status e categoria respeitando
  permissões por papel.
- Calcular créditos por categoria para verificação dos fatos creditos_grupo_* do motor.
"""
