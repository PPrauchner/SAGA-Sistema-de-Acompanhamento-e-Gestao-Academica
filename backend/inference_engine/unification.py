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
