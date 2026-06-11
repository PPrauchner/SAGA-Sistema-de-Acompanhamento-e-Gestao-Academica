"""
Regra RL05 — Pontuação Ponderada de Produção (declarativa).

Responsabilidades:
- Declarar a cláusula: pontuacao_producao(P, Score) :- producao_veiculo(P, V),
  nivel_relevancia(V, Prog, Nivel), relevancia_peso(Nivel, Peso), pontuacao_base(P, Base),
  Score = Base * Peso (built-in aritmético).
- Fatos de configuração de pesos: relevancia_peso('A1', 2.0), relevancia_peso('A2', 1.5),
  relevancia_peso('B', 1.0), relevancia_peso('C', 0.5) — carregados da coleção
  programs/prog_default/vehicle_levels/ pelo InferenceService.
- Executada em ProductionService.create_production() e em GET /api/v1/inference/{student_id}.
- Casos de teste: producao_A1_base10 → Score=20.0, producao_B_base10 → Score=10.0,
  producao_C_base10 → Score=5.0.
"""

from inference_engine.terms import Compound, Variable


def register(rule_base) -> None:
    producao = Variable("Producao")
    veiculo = Variable("Veiculo")
    nivel = Variable("Nivel")

    peso = Variable("Peso")
    base = Variable("Base")
    score = Variable("Score")

    programa = Variable("Programa")

    rule_base.add_rule(
        Compound("pontuacao_producao", [producao, score]),
        [
            Compound("producao_veiculo", [producao, veiculo]),
            Compound("nivel_relevancia", [veiculo, programa, nivel]),
            Compound("relevancia_peso", [nivel, peso]),
            Compound("pontuacao_base", [producao, base]),
            Compound("mul", [base, peso, score]),
        ],
    )
