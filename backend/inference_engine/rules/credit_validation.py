"""
Regra RL02 — Validação de Créditos por Grupo (declarativa).

Responsabilidades:
- Declarar a cláusula: creditos_validos(A) com body verificando créditos por grupo:
  creditos_grupo_basico(A, N1) e N1 >= min_creditos_basico(Prog, Min1); análogo para
  especifico (>=) e tecnologico (<=); total_creditos(A, T) >= min_creditos_total.
- Comparações aritméticas (>=, <=) tratadas como built-ins no Resolver via Compound('gte'
  e 'lte').
- Exportar fatos de configuração padrão: min_creditos_basico('prog_default', 12),
  min_creditos_especifico('prog_default', 8), max_creditos_tecnologico('prog_default', 4),
  min_creditos_total('prog_default', 24) — a serem carregados na FactBase pelo
  InferenceService a partir de programs/prog_default no Firestore.
- Casos de teste: creditos_validos, basico_insuficiente, tecnologico_excedido,
  total_insuficiente.
"""
