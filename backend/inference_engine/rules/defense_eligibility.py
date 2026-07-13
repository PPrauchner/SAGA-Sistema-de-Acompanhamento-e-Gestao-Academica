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

from __future__ import annotations

from inference_engine.terms import Compound, Variable

_A = Variable("A")

# apto_defesa(A) :- creditos_validos(A), proficiencia_comprovada(A),
#                   qualificacao_aprovada(A), producao_bibliografica_validada(A),
#                   plano_concluido(A).
CLAUSES: list[tuple[Compound, list[Compound]]] = [
    (
        Compound("apto_defesa", [_A]),
        [
            Compound("creditos_validos", [_A]),
            Compound("proficiencia_comprovada", [_A]),
            Compound("qualificacao_aprovada", [_A]),
            Compound("producao_bibliografica_validada", [_A]),
            Compound("plano_concluido", [_A]),
        ],
    ),
]
