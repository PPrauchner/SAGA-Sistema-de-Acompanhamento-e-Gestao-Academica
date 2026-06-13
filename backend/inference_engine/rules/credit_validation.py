"""
Regra RL02 — Validação de Créditos por Grupo (declarativa).

Responsabilidades:
- Declarar a cláusula: creditos_validos(A) com body verificando créditos por grupo:
  creditos_grupo_basico(A, N1) e N1 >= min_creditos_basico(Prog, Min1); análogo para
  especifico (>=) e tecnologico (<=); total_creditos(A, T) >= min_creditos_total.
- Comparações aritméticas (>=, <=) tratadas como built-ins no Resolver via Compound('gte'
  e 'lte').
- Exportar fatos de configuração padrão: min_creditos_basico('prog_default', 12),
  min_creditos_especifico('prog_default', 8), max_creditos_tecnologico('prog_default', 4),
  min_creditos_total('prog_default', 24) — a serem carregados na FactBase pelo
  InferenceService a partir de programs/prog_default no Firestore.
- Casos de teste: creditos_validos, basico_insuficiente, tecnologico_excedido,
  total_insuficiente.
"""

from __future__ import annotations

from inference_engine.terms import Variable, Compound
from inference_engine.knowledge_base import RuleBase


def register(rb: RuleBase) -> None:
    """Registra RL02 na RuleBase fornecida.

    Args:
        rb: RuleBase onde a regra será adicionada.
    """
    A    = Variable("A")
    P    = Variable("P")
    N1   = Variable("N1")
    N2   = Variable("N2")
    N3   = Variable("N3")
    T    = Variable("T")
    Min1 = Variable("Min1")
    Min2 = Variable("Min2")
    Max3 = Variable("Max3")
    MinT = Variable("MinT")

    head = Compound("creditos_validos", [A])
    body = [
        Compound("creditos_grupo_basico",      [A, N1]),
        Compound("min_creditos_basico",        [P, Min1]),
        Compound("gte",                        [N1, Min1]),
        Compound("creditos_grupo_especifico",  [A, N2]),
        Compound("min_creditos_especifico",    [P, Min2]),
        Compound("gte",                        [N2, Min2]),
        Compound("creditos_grupo_tecnologico", [A, N3]),
        Compound("max_creditos_tecnologico",   [P, Max3]),
        Compound("lte",                        [N3, Max3]),
        Compound("total_creditos",             [A, T]),
        Compound("min_creditos_total",         [P, MinT]),
        Compound("gte",                        [T, MinT]),
    ]
    rb.add_rule(head, body)
