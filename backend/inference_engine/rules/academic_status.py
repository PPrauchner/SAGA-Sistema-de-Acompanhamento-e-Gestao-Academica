"""
Regra RL03 — Situação Acadêmica Em Risco (declarativa, 4 cláusulas alternativas).

Responsabilidades:
- Declarar 4 cláusulas alternativas para em_risco(A) (OR implícito, sem NAF):
    1. em_risco(A) :- prazo_estourado(A).
    2. em_risco(A) :- creditos_insuficientes(A).
    3. em_risco(A) :- qualificacao_pendente(A), prazo_qualificacao_proximo(A).
    4. em_risco(A) :- plano_atrasado(A).
- Cada cláusula é independente — basta uma ser satisfeita para em_risco ser verdadeiro.
- Fatos derivados (prazo_estourado, plano_atrasado, qualificacao_pendente etc.) são
  calculados e inseridos na FactBase pelo InferenceService antes de cada consulta.
- Casos de teste: em_risco_prazo, em_risco_qualificacao, em_risco_plano_atrasado, regular.
"""

from inference_engine.terms import Compound, Variable


def register(rule_base) -> None:
    aluno = Variable("Aluno")

    rule_base.add_rule(
        Compound("em_risco", [aluno]),
        [
            Compound("prazo_estourado", [aluno]),
        ],
    )

    rule_base.add_rule(
        Compound("em_risco", [aluno]),
        [
            Compound("creditos_insuficientes", [aluno]),
        ],
    )

    rule_base.add_rule(
        Compound("em_risco", [aluno]),
        [
            Compound("qualificacao_pendente", [aluno]),
            Compound("prazo_qualificacao_proximo", [aluno]),
        ],
    )

    rule_base.add_rule(
        Compound("em_risco", [aluno]),
        [
            Compound("plano_atrasado", [aluno]),
        ],
    )
