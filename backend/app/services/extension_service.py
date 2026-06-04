"""
Serviço de negócio para gestão de solicitações de prorrogação de prazo.

Responsabilidades:
- request_extension(): aluno solicita prorrogação. Verifica se não atingiu max_prorrogacoes
  e se não há solicitação pendente. Decorado com @requires_role('aluno'),
  @audit_operation e @check_deadlines.
- advisor_review(): orientador registra parecer sobre a prorrogação.
  Decorado com @requires_role('orientador') e @audit_operation.
- approve_extension(): coordenação aprova ou rejeita. Se aprovada, atualiza prazo_final
  do aluno e registra situacao_registrada='em_prorrogacao'. Decorado com
  @requires_role('coordenacao'), @audit_operation e @trigger_alerts (notifica aluno).
"""
