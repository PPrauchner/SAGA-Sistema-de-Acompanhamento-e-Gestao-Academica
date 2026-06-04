"""
Testes unitários pytest para o módulo inference_engine/substitution.py.

Responsabilidades:
- Testar apply(Atom, subst) → retorna o Atom inalterado.
- Testar apply(Variable(X), subst) com X em subst → retorna apply(subst[X], subst).
- Testar apply(Variable(X), subst) com X fora de subst → retorna Variable(X).
- Testar apply(Compound, subst) → retorna Compound com args aplicados recursivamente.
- Testar substituição encadeada: Variable(X) → Variable(Y), Variable(Y) → Atom.
"""
