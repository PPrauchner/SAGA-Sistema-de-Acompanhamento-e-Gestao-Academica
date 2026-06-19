"""
Regra RL05 — Pontuação Ponderada de Produção (declarativa).

Responsabilidades:
- Declarar a cláusula: pontuacao_producao(P, Score) :- producao_veiculo(P, V),
  nivel_relevancia(V, Prog, Nivel), relevancia_peso(Nivel, Peso), pontuacao_base(P, Base),
  Score = Base * Peso (built-in aritmético).
- Fatos de configuração de pesos (configuráveis), escala Qualis Único de 7 níveis:
  relevancia_peso('A1', 1.0), relevancia_peso('A2', 0.85), relevancia_peso('A3', 0.7),
  relevancia_peso('A4', 0.7), relevancia_peso('B1', 0.5), relevancia_peso('B2', 0.5),
  relevancia_peso('SC', 0.2) — carregados da coleção programs/prog_default/vehicle_levels/
  pelo InferenceService. Veículo sem nível configurado usa o fallback 'SC' (peso 0.2).
- Executada em ProductionService.create_production() e em GET /api/v1/inference/{student_id}.
- A regra é aritmética pura (Score = Base * Peso); os testes em tests/test_rules.py exercitam
  combinações arbitrárias de peso/base independentes da configuração padrão acima.
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
