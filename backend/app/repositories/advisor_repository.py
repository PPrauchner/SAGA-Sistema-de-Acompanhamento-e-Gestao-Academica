"""
Repositório concreto para operações na coleção advisors/.

Responsabilidades:
- Herdar FirebaseRepository e especializar operações para a coleção advisors/.
- get_advisor(advisor_id), create_advisor(data), update_advisor(advisor_id, data),
  delete_advisor(advisor_id): CRUD básico.
- get_advisors_with_student_count(): lista orientadores enriquecidos com contagem de
  orientandos_ativos via query na coleção students/ filtrada por orientador_id e
  situacao_registrada não-terminal.
- check_advisor_capacity(advisor_id): verifica se orientador ainda está abaixo do
  limite_orientandos configurado.
"""
