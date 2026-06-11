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
from inference_engine.terms import Compound, Variable


def register(rule_base) -> None:
    aluno = Variable("Aluno")
    programa = Variable("Programa")

    basico = Variable("Basico")
    especifico = Variable("Especifico")
    tecnologico = Variable("Tecnologico")
    total = Variable("Total")

    min_basico = Variable("MinBasico")
    min_especifico = Variable("MinEspecifico")
    max_tecnologico = Variable("MaxTecnologico")
    min_total = Variable("MinTotal")

    rule_base.add_rule(
        Compound("creditos_validos", [aluno]),
        [
            Compound("creditos_grupo_basico", [aluno, basico]),
            Compound("creditos_grupo_especifico", [aluno, especifico]),
            Compound("creditos_grupo_tecnologico", [aluno, tecnologico]),
            Compound("total_creditos", [aluno, total]),
            Compound("min_creditos_basico", [programa, min_basico]),
            Compound("min_creditos_especifico", [programa, min_especifico]),
            Compound("max_creditos_tecnologico", [programa, max_tecnologico]),
            Compound("min_creditos_total", [programa, min_total]),
            Compound("gte", [basico, min_basico]),
            Compound("gte", [especifico, min_especifico]),
            Compound("lte", [tecnologico, max_tecnologico]),
            Compound("gte", [total, min_total]),
        ],
    )