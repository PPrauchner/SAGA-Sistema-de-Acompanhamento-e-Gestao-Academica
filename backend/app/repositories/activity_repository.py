"""
Repositório concreto para as sub-coleções de atividades e produções no Firestore.

Responsabilidades:
- Acessar e persistir dados em students/{id}/activities/ e students/{id}/productions/.
- Métodos de atividade: create_activity(student_id, data), get_activity(activity_id),
  update_activity(activity_id, data), list_activities(student_id, filters).
- Métodos de produção: create_production(student_id, data), list_productions(student_id).
- get_approved_activities_by_category(student_id): agrega créditos por categoria
  (básico, específico, tecnológico) para alimentar os fatos creditos_grupo_* do motor.
- get_approved_productions(student_id): lista produções aprovadas para verificação do
  fato producao_bibliografica_validada.
- Salvar histórico de tipos de atividade em activity_types/{id}/history/ para o aspecto A03.
"""
