"""
Serviço de negócio para geração de relatórios gerenciais da coordenação.

Responsabilidades:
- get_students_at_risk(): alunos com situacao_inferida em risco. Decorado com
  @requires_role('coordenacao') e @audit_operation.
- get_students_by_status(): contagem e lista de alunos agrupados por situacao_registrada.
- get_students_by_advisor(): alunos agrupados por orientador com distribuição de status.
- get_completion_time_avg(): calcula média, mínimo e máximo de (data_conclusao -
  data_ingresso) para alunos com situacao_registrada='concluido'.
- get_productions_report(): produção bibliográfica por aluno e por orientador com pontuação
  total e distribuição por nível de relevância (A1/A2/B/C). Decorado com @audit_operation.
- Todos os métodos trabalham exclusivamente com dados do Firestore — não executam o motor
  de inferência em tempo real.
"""
