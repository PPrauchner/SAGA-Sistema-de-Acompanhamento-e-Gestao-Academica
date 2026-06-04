"""
Serviço de negócio para registro e pontuação de produções bibliográficas.

Responsabilidades:
- create_production(): cria produção e atividade associada no Firestore. Executa motor RL05
  via InferenceService imediatamente para calcular pontuacao_calculada, nivel_veiculo e
  peso_aplicado a partir do nível de relevância do veículo em programs/vehicle_levels/.
  Decorado com @requires_role('aluno'), @audit_operation e @check_deadlines.
- list_productions(): lista produções enriquecidas com veiculo_nome, nivel e pontuação.
- Verificar existência de ao menos 1 produção aprovada para inserir o fato
  producao_bibliografica_validada(student_id) na FactBase do motor.
"""
