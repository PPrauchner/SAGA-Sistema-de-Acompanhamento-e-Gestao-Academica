"""
Serviço de negócio para agregação de dados dos dashboards dos três perfis.

Responsabilidades:
- get_aluno_dashboard(student_id) -> AlunoDashboardResponse: agrega situação atual,
  progresso do plano, créditos por grupo, resumo do checklist, tasks próximas, produções
  aprovadas e atividades pendentes de validação. Exibe badge de conflito se
  situacao_registrada != situacao_inferida.
- get_orientador_dashboard(advisor_id) -> OrientadorDashboardResponse: visão agregada dos
  orientandos — contagem por status, atividades aguardando parecer, lista de orientandos
  com progresso e alertas.
- get_coordenacao_dashboard() -> CoordDashboardResponse: visão macro do programa — totais
  por status, atividades aguardando validação, prorrogações pendentes, produções do último
  mês, tempo médio de integralização e auditoria recente.
"""
