"""
Router FastAPI para os endpoints de solicitações de prorrogação de prazo.

Responsabilidades:
- GET /api/v1/extensions: lista prorrogações. Aluno vê as próprias; coordenação vê todas.
  Aplica @requires_role para todos os papéis.
- POST /api/v1/extensions: aluno solicita prorrogação de prazo. Aplica
  @requires_role('aluno'), @audit_operation e @check_deadlines (verifica se aluno não
  atingiu max_prorrogacoes e ainda está dentro do período elegível para solicitar).
- PATCH /api/v1/extensions/{extension_id}/review: orientador emite parecer sem aprovar.
  Aplica @requires_role('orientador') e @audit_operation.
- PATCH /api/v1/extensions/{extension_id}/approve: coordenação aprova ou rejeita. Se
  aprovada, atualiza prazo_final do aluno. Aplica @requires_role('coordenacao'),
  @audit_operation e @trigger_alerts (notifica aluno com resultado e novo prazo).
"""
