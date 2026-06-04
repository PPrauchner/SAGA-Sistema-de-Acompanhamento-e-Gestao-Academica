"""
Agregador de FactBase e RuleBase — interface única de consulta do motor de inferência.

Responsabilidades:
- Definir FactBase: coleção de Compounds verdadeiros. Métodos: add_fact(compound),
  get_facts(). Populada pelo InferenceService (backend/app/services/inference_service.py)
  antes de cada consulta a partir do Firestore.
- Definir RuleBase: coleção de cláusulas (head: Compound, body: list[Compound]).
  Métodos: add_rule(head, body), get_rules(). Regras importadas dos módulos em rules/.
- Definir InferenceEngine: orquestra FactBase + RuleBase + Resolver. Único ponto de
  acesso externo ao motor. Método público: query(goal: Term) -> list[dict] — executa
  solve(goal, self, {}) e coleta todos os resultados em lista.
- Módulo isolado: depende apenas de terms.py, resolver.py e dos módulos em rules/.
  Sem imports de FastAPI, Firebase ou qualquer ORM.
"""
