"""
Testes unitários pytest para as 5 regras em inference_engine/rules/.

Responsabilidades:
- RL01 defense_eligibility: testar cenários apto (5 fatos presentes), inapto_sem_producao,
  inapto_creditos_invalidos (cada fato faltando individualmente).
- RL02 credit_validation: testar creditos_validos (todos os grupos corretos),
  basico_insuficiente, tecnologico_excedido, total_insuficiente.
- RL03 academic_status: testar em_risco_prazo (prazo_estourado presente), em_risco_qualificacao
  (qualificacao_pendente + prazo_qualificacao_proximo), em_risco_plano_atrasado, regular
  (nenhum fato de risco presente → em_risco retorna False).
- RL04 activity_eligibility: testar elegivel (4 fatos), sem_comprovante, tipo_inativo,
  excede_limite_tecnologico.
- RL05 production_scoring: testar producao_A1_base10 → Score=20.0, producao_B_base10 →
  Score=10.0, producao_C_base10 → Score=5.0.
"""
