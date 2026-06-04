"""
Testes unitários pytest para o módulo inference_engine/terms.py.

Responsabilidades:
- Testar instanciação e igualdade de Atom: str, int, float e bool.
- Testar instanciação e igualdade de Variable por nome.
- Testar instanciação de Compound com functor e argumentos aninhados.
- Testar que Term aceita Atom, Variable e Compound (checagem de tipo).
- Garantir imutabilidade de Atom (sem alteração de valor após criação).
"""
