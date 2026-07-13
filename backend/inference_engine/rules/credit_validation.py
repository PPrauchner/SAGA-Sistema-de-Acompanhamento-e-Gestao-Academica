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

from inference_engine.terms import Compound, Variable

_A = Variable("A")
_P = Variable("P")  # Único programa: os 4 fatos de configuração compartilham o mesmo P.
_N1, _N2, _N3, _T = Variable("N1"), Variable("N2"), Variable("N3"), Variable("T")
_MIN1, _MIN2, _MAX3, _MINT = (
    Variable("Min1"),
    Variable("Min2"),
    Variable("Max3"),
    Variable("MinT"),
)

# creditos_validos(A) :-
#   creditos_grupo_basico(A, N1),      min_creditos_basico(P, Min1),     gte(N1, Min1),
#   creditos_grupo_especifico(A, N2),  min_creditos_especifico(P, Min2), gte(N2, Min2),
#   creditos_grupo_tecnologico(A, N3), max_creditos_tecnologico(P, Max3), lte(N3, Max3),
#   total_creditos(A, T),              min_creditos_total(P, MinT),       gte(T, MinT).
CLAUSES: list[tuple[Compound, list[Compound]]] = [
    (
        Compound("creditos_validos", [_A]),
        [
            Compound("creditos_grupo_basico", [_A, _N1]),
            Compound("min_creditos_basico", [_P, _MIN1]),
            Compound("gte", [_N1, _MIN1]),
            Compound("creditos_grupo_especifico", [_A, _N2]),
            Compound("min_creditos_especifico", [_P, _MIN2]),
            Compound("gte", [_N2, _MIN2]),
            Compound("creditos_grupo_tecnologico", [_A, _N3]),
            Compound("max_creditos_tecnologico", [_P, _MAX3]),
            Compound("lte", [_N3, _MAX3]),
            Compound("total_creditos", [_A, _T]),
            Compound("min_creditos_total", [_P, _MINT]),
            Compound("gte", [_T, _MINT]),
        ],
    ),
]
