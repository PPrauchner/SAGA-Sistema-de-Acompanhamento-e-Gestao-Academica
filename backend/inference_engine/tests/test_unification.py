"""
Testes unitários pytest para o módulo inference_engine/unification.py.

Responsabilidades:
- Testar unify(Atom, Atom) com mesmo valor → retorna subst inalterada.
- Testar unify(Atom, Atom) com valores diferentes → retorna None.
- Testar unify(Variable(X), Atom) quando X não está em subst → retorna {X: Atom}.
- Testar unify(Variable(X), term) quando X já está em subst → unifica subst[X] com term.
- Testar occur check: Variable(X) não pode ser unificado com Compound contendo X.
- Testar unify(Compound, Compound) com mesmo functor e aridade → unifica argumentos par a par.
- Testar unify(Compound, Compound) com functores ou aridades diferentes → retorna None.
"""
