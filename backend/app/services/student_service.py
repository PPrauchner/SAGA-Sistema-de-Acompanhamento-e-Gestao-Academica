"""
Serviço de negócio para gestão de discentes.

Responsabilidades:
- Implementar CRUD completo de alunos delegando persistência ao StudentRepository.
- create_student(): cria aluno no Firestore e dispara convite de primeiro acesso.
  Decorado com @requires_role('coordenacao') e @audit_operation.
- update_student(): atualiza campos editáveis do aluno.
  Decorado com @requires_role('coordenacao') e @audit_operation.
- delete_student(): remove aluno verificando ausência de dependências ativas.
  Decorado com @requires_role('coordenacao') e @audit_operation.
- update_qualificacao(): registra aprovação na qualificação. Gera fato qualificacao_aprovada
  para o motor. Decorado com @requires_role('coordenacao'), @audit_operation e @track_history.
- update_proficiencia(): registra comprovação de proficiência em língua estrangeira.
  Decorado com @requires_role('coordenacao'), @audit_operation e @track_history.
- update_situacao_registrada(): atualiza situação registrada manualmente.
  Decorado com @requires_role('coordenacao'), @audit_operation e @track_history.
  Coberto pelo aspecto A03 (histórico) via metaclasse HistoryMeta ou decorador @track_history.
"""
