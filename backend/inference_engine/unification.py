"""
Algoritmo de unificação entre termos do motor de inferência.

Responsabilidades:
- Implementar `def unify(t1: Term, t2: Term, subst: dict) -> dict | None`.
- Casos tratados:
    - Atom == Atom com mesmo valor → retorna subst inalterada.
    - Atom != Atom → retorna None.
    - Variable(X) já em subst → unifica subst[X] com t2 recursivamente.
    - Variable(X) não em subst → retorna {**subst, X: t2} com occur check
      (X não pode aparecer em t2).
    - Compound vs Compound → mesmo functor e aridade; unifica argumentos par a par.
    - Qualquer outra combinação → retorna None.
- Módulo isolado: depende apenas de terms.py, sem imports externos.
"""

from __future__ import annotations

from inference_engine.terms import Atom, Variable, Compound, Term
from inference_engine.substitution import apply


def _occurs(var: Variable, term: Term, subst: dict[str, Term]) -> bool:
    """Verifica se `var` ocorre em `term` após aplicar `subst` (occur check)."""
    term = apply(term, subst)
    if isinstance(term, Variable):
        return term.name == var.name
    if isinstance(term, Compound):
        return any(_occurs(var, arg, subst) for arg in term.args)
    return False


def unify(t1: Term, t2: Term, subst: dict[str, Term]) -> dict[str, Term] | None:
    """Unifica dois termos sob a substituição parcial `subst`.

    Args:
        t1: Primeiro termo.
        t2: Segundo termo.
        subst: Substituição parcial acumulada.

    Returns:
        Substituição estendida se bem-sucedida, None caso contrário.
    """
    t1 = apply(t1, subst)
    t2 = apply(t2, subst)

    if isinstance(t1, Atom) and isinstance(t2, Atom):
        return subst if t1.value == t2.value else None

    if isinstance(t1, Variable):
        if isinstance(t2, Variable) and t1.name == t2.name:
            return subst
        if _occurs(t1, t2, subst):
            return None
        return {**subst, t1.name: t2}

    if isinstance(t2, Variable):
        if _occurs(t2, t1, subst):
            return None
        return {**subst, t2.name: t1}

    if isinstance(t1, Compound) and isinstance(t2, Compound):
        if t1.functor != t2.functor or len(t1.args) != len(t2.args):
            return None
        current = subst
        for a1, a2 in zip(t1.args, t2.args):
            current = unify(a1, a2, current)
            if current is None:
                return None
        return current

    return None
