"""
Estratégia de resolução direta sem backtracking do motor de inferência.

Responsabilidades:
- Implementar `def solve(goal: Term, kb: KnowledgeBase, subst: dict) -> Iterator[dict]`.
- Algoritmo:
    1. Verifica se goal está na FactBase com unificação — se sim, yield substituição.
    2. Para cada cláusula (head, body) da RuleBase: renomeia variáveis para evitar
       colisão; tenta unify(goal, head, subst); se bem-sucedido, resolve cada condição
       do body sequencialmente acumulando substituições.
    3. Sem backtracking: não testa caminhos alternativos após falha parcial em conjunção.
- Tratar built-ins aritméticos: Compound('gte', [...]) e Compound('lte', [...]) são
  resolvidos calculando valores após aplicar substituições, não via FactBase.
- Módulo isolado: depende de terms.py, unification.py, substitution.py e knowledge_base.py.
"""
