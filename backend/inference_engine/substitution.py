"""
Representação e aplicação de substituições variável→valor no motor de inferência.

Responsabilidades:
- Definir o tipo substituição como dict[str, Term].
- Implementar `def apply(term: Term, subst: dict) -> Term`:
    - Atom → retorna inalterado.
    - Variable(X) em subst → aplica recursivamente apply(subst[X], subst).
    - Variable(X) fora de subst → retorna Variable(X).
    - Compound → retorna Compound(functor, [apply(arg, subst) for arg in args]).
- Módulo isolado: depende apenas de terms.py, sem imports externos.
"""

from __future__ import annotations

from inference_engine.terms import Atom, Variable, Compound, Term


def apply(term: Term, subst: dict[str, Term]) -> Term:
    """Aplica a substituição `subst` ao `term` recursivamente.

    Args:
        term: Termo a resolver.
        subst: Mapeamento variável→Term acumulado.

    Returns:
        Termo com todas as variáveis substituídas que couberem em `subst`.
    """
    if isinstance(term, Atom):
        return term
    if isinstance(term, Variable):
        if term.name in subst:
            return apply(subst[term.name], subst)
        return term
    # Compound
    return Compound(term.functor, [apply(arg, subst) for arg in term.args])
