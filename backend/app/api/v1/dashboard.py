"""
Router FastAPI para os endpoints de dashboard dos três perfis de usuário.

Responsabilidades:
- GET /api/v1/dashboard/aluno/{student_id}: dados do dashboard do aluno — situação atual,
  progresso do plano, créditos por grupo, resumo do checklist, tasks próximas, produções
  aprovadas e atividades pendentes de validação. Aplica @requires_role para aluno (próprio),
  orientador e coordenação.
- GET /api/v1/dashboard/orientador/{advisor_id}: visão agregada dos orientandos do
  orientador — contagem por status, atividades aguardando parecer, lista de orientandos com
  alertas. Aplica @requires_role('orientador', 'coordenacao').
- GET /api/v1/dashboard/coordenacao: visão macro do programa — totais por status,
  atividades aguardando validação, prorrogações pendentes, produções do último mês, tempo
  médio de integralização e auditoria recente. Exclusivo de @requires_role('coordenacao').
"""
