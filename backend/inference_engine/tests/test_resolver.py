"""
Testes unitários pytest para o módulo inference_engine/resolver.py.

Responsabilidades:
- Testar solve() com goal que unifica diretamente com fato na FactBase → yield substituição.
- Testar solve() com goal que requer encadeamento de regra (head + body) → yield substituição.
- Testar solve() quando nenhum fato ou regra satisfaz o goal → iterador vazio.
- Testar solve() com built-in aritmético Compound('gte', [Atom(14), Atom(12)]) → resolvido.
- Testar que renomeação de variáveis evita colisão entre cláusulas da RuleBase.
- Testar ausência de backtracking: falha parcial em body não tenta caminho alternativo.
"""
