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

from __future__ import annotations

from inference_engine.terms import Compound, Variable

_P = Variable("P")
_V = Variable("V")
_PROG = Variable("Prog")
_NIVEL = Variable("Nivel")
_PESO = Variable("Peso")
_BASE = Variable("Base")
_SCORE = Variable("Score")

# pontuacao_producao(P, Score) :- producao_veiculo(P, V), nivel_relevancia(V, Prog, Nivel),
#   relevancia_peso(Nivel, Peso), pontuacao_base(P, Base), mul(Base, Peso, Score).
CLAUSES: list[tuple[Compound, list[Compound]]] = [
    (
        Compound("pontuacao_producao", [_P, _SCORE]),
        [
            Compound("producao_veiculo", [_P, _V]),
            Compound("nivel_relevancia", [_V, _PROG, _NIVEL]),
            Compound("relevancia_peso", [_NIVEL, _PESO]),
            Compound("pontuacao_base", [_P, _BASE]),
            Compound("mul", [_BASE, _PESO, _SCORE]),
        ],
    ),
]
