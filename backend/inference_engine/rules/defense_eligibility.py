"""
Regra RL01 — Aptidão à Defesa (declarativa).

Responsabilidades:
- Declarar a cláusula: apto_defesa(A) :- creditos_validos(A), proficiencia_comprovada(A),
  qualificacao_aprovada(A), producao_bibliografica_validada(A), plano_concluido(A).
- Todas as 5 condições devem ser satisfeitas simultaneamente (conjunção).
- Exportar a cláusula em formato compatível com RuleBase: (head: Compound, body: list[Compound]).
- Módulo puramente declarativo — alterar a política de defesa requer alterar este arquivo,
  não a lógica de fluxo de controle.
- Casos de teste cobertos em inference_engine/tests/test_rules.py: cenário apto (todas as
  5 condições presentes), inapto_sem_producao, inapto_creditos_invalidos.
"""
