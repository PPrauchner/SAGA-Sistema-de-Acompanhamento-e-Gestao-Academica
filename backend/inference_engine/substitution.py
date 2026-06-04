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
