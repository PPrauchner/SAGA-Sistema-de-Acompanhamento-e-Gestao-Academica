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

from inference_engine.terms import Variable, Compound
from inference_engine.knowledge_base import RuleBase


def register(rb: RuleBase) -> None:
    """Registra RL05 na RuleBase fornecida.

    Args:
        rb: RuleBase onde a regra será adicionada.
    """
    P     = Variable("P")
    V     = Variable("V")
    Prog  = Variable("Prog")
    Nivel = Variable("Nivel")
    Peso  = Variable("Peso")
    Base  = Variable("Base")
    Score = Variable("Score")

    head = Compound("pontuacao_producao", [P, Score])
    body = [
        Compound("producao_veiculo",  [P, V]),
        Compound("nivel_relevancia",  [V, Prog, Nivel]),
        Compound("relevancia_peso",   [Nivel, Peso]),
        Compound("pontuacao_base",    [P, Base]),
        Compound("mul",               [Base, Peso, Score]),
    ]
    rb.add_rule(head, body)
