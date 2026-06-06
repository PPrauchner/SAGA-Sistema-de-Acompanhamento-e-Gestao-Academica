"""
resolver.py
===========
Módulo   : Motor de Inferência Lógica
Versão   : 1.0.0-MVP
Spec     : docs/specs/01_motor_inferencia.json → modulos.resolver.py

Responsabilidade
----------------
Estratégia de resolução direta (forward-chaining por conjunção) sem backtracking.
Expõe uma única função pública:

    solve(goal, kb, subst) -> Iterator[dict]

Algoritmo (conforme spec §modulos.resolver.py.algoritmo)
---------------------------------------------------------
1. Aplica substituições pendentes ao goal antes de qualquer comparação.
2. Verifica se o goal é um built-in aritmético (gte, lte, mul) — executa e retorna.
3. Tenta unificar o goal com cada fato da FactBase — yield da substituição resultante.
4. Para cada cláusula (head, body) da RuleBase:
   a. Renomeia variáveis da cláusula com sufixo único para evitar colisão.
   b. Tenta unify(goal, head, subst).
   c. Se bem-sucedido, resolve cada condição do body sequencialmente,
      acumulando substituições ao longo da conjunção.
5. Sem backtracking: se uma conjunção falha parcialmente, a cláusula é descartada
   inteiramente e o motor passa para a próxima, sem tentar caminhos alternativos.

Built-ins suportados (spec §nota_implementacao de RL02 e RL05)
--------------------------------------------------------------
  gte(X, Y)    → sucesso se valor(X) >= valor(Y)
  lte(X, Y)    → sucesso se valor(X) <= valor(Y)
  mul(X, Y, Z) → unifica Z com X * Y  (usado em RL05 para Score = Base * Peso)

Dependências internas
---------------------
  inference_engine.terms        — Atom, Variable, Compound, Term
  inference_engine.unification  — unify()
  inference_engine.substitution — apply()

Dependências externas
---------------------
  NENHUMA — módulo completamente isolado de FastAPI e Firebase.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Iterator

from inference_engine.terms import Atom, Variable, Compound, Term
from inference_engine.unification import unify
from inference_engine.substitution import apply

if TYPE_CHECKING:
    # Importação apenas para type hints — evita import circular em runtime.
    from inference_engine.knowledge_base import KnowledgeBase


# ---------------------------------------------------------------------------
# Contador de instâncias de cláusulas
# ---------------------------------------------------------------------------

# Garante que cada aplicação de regra recebe variáveis únicas.
# Ex: a regra apto_defesa(A) aplicada duas vezes produz A_1 e A_2,
# nunca conflitando na mesma substituição.
_clause_counter: int = 0


# ---------------------------------------------------------------------------
# Funções auxiliares privadas
# ---------------------------------------------------------------------------

def _rename_clause(
    head: Compound,
    body: list[Compound],
) -> tuple[Compound, list[Compound]]:
    """
    Renomeia todas as variáveis de uma cláusula com um sufixo único (_N).

    Necessário porque o mesmo módulo de regra pode ser aplicado múltiplas vezes
    durante a resolução de uma consulta. Sem renaming, variáveis de instâncias
    distintas da mesma regra colidiriam na substituição acumulada.

    Parâmetros
    ----------
    head : Compound
        Cabeça da cláusula (ex: Compound('apto_defesa', [Variable('A')])).
    body : list[Compound]
        Lista de condições do corpo da cláusula.

    Retorna
    -------
    tuple[Compound, list[Compound]]
        (head renomeado, body renomeado) com variáveis frescas.
    """
    global _clause_counter
    _clause_counter += 1
    suffix = f"_{_clause_counter}"

    def _rename_term(term: Term) -> Term:
        if isinstance(term, Variable):
            return Variable(term.name + suffix)
        if isinstance(term, Compound):
            return Compound(term.functor, [_rename_term(arg) for arg in term.args])
        return term  # Atom: imutável, não precisa de renaming

    renamed_head = _rename_term(head)
    renamed_body = [_rename_term(cond) for cond in body]
    return renamed_head, renamed_body


def _resolve_builtin(
    goal: Compound,
    subst: dict[str, Term],
) -> Iterator[dict]:
    """
    Executa predicados aritméticos built-in que não existem na FactBase nem na RuleBase.

    Os built-ins são identificados pelo functor do goal antes de qualquer consulta
    à base de conhecimento (ver solve() — Passo 2).

    Built-ins implementados
    -----------------------
    gte(X, Y)
        Sucesso se o valor resolvido de X >= valor resolvido de Y.
        Usado em RL02 para verificar mínimos de crédito.

    lte(X, Y)
        Sucesso se o valor resolvido de X <= valor resolvido de Y.
        Usado em RL02 para verificar máximo de créditos tecnológicos.

    mul(X, Y, Z)
        Unifica Z com o produto X * Y.
        Usado em RL05 para calcular Score = Base * Peso.

    Parâmetros
    ----------
    goal  : Compound — goal já com substituições aplicadas.
    subst : dict     — substituição corrente.

    Yields
    ------
    dict : substituição estendida em caso de sucesso; nada em caso de falha.
    """
    functor = goal.functor

    # --- gte / lte -----------------------------------------------------------
    if functor in ("gte", "lte") and len(goal.args) == 2:
        left  = apply(goal.args[0], subst)
        right = apply(goal.args[1], subst)

        if isinstance(left, Atom) and isinstance(right, Atom):
            try:
                lv = float(left.value)
                rv = float(right.value)
                succeeded = (lv >= rv) if functor == "gte" else (lv <= rv)
                if succeeded:
                    yield subst
            except (TypeError, ValueError):
                pass  # Operandos não numéricos → falha silenciosa

    # --- mul -----------------------------------------------------------------
    elif functor == "mul" and len(goal.args) == 3:
        left       = apply(goal.args[0], subst)
        right      = apply(goal.args[1], subst)
        result_var = goal.args[2]  # Pode ser Variable ou Atom já vinculado

        if isinstance(left, Atom) and isinstance(right, Atom):
            try:
                product   = float(left.value) * float(right.value)
                new_subst = unify(result_var, Atom(product), subst)
                if new_subst is not None:
                    yield new_subst
            except (TypeError, ValueError):
                pass


# Conjunto de functors tratados como built-ins — verificado em solve() antes
# de consultar a FactBase ou a RuleBase.
_BUILTINS: frozenset[str] = frozenset({"gte", "lte", "mul"})


# ---------------------------------------------------------------------------
# Função pública
# ---------------------------------------------------------------------------

def solve(
    goal: Term,
    kb: "KnowledgeBase",
    subst: dict[str, Term],
) -> Iterator[dict]:
    """
    Resolve um goal contra a base de conhecimento dada a substituição corrente.

    Esta é a única função pública do módulo. O InferenceEngine a chama com
    subst={} para iniciar uma consulta; chamadas recursivas acumulam substituições
    ao resolver condições do corpo de uma regra.

    Parâmetros
    ----------
    goal  : Term            — o predicado a provar (deve ser Compound após apply).
    kb    : KnowledgeBase   — contém fact_base e rule_base acessíveis pelo resolver.
    subst : dict[str, Term] — substituição acumulada até este ponto da resolução.

    Yields
    ------
    dict[str, Term]
        Cada substituição que torna o goal verdadeiro.
        Sem resultados = goal não provável com os fatos e regras atuais.

    Comportamento sem backtracking
    ------------------------------
    Se ao resolver uma conjunção A, B, C a condição B falha, o motor descarta
    a cláusula inteira e passa para a próxima. Não retoma alternativas dentro
    da mesma cláusula.
    """
    # Passo 1 — aplica substituições pendentes para trabalhar com o goal resolvido.
    resolved_goal = apply(goal, subst)

    # Goals que não são Compound (Variable solta, Atom) são inválidos aqui.
    if not isinstance(resolved_goal, Compound):
        return

    # Passo 2 — built-ins têm prioridade; nunca entram na FactBase/RuleBase.
    if resolved_goal.functor in _BUILTINS:
        yield from _resolve_builtin(resolved_goal, subst)
        return

    # Passo 3 — tentativa de unificação direta com fatos da FactBase.
    for fact in kb.fact_base.get_facts():
        result = unify(resolved_goal, fact, subst)
        if result is not None:
            yield result

    # Passo 4 — tentativa de aplicação de cada regra da RuleBase.
    for head, body in kb.rule_base.get_rules():

        # 4a. Variáveis frescas para esta instância da regra.
        fresh_head, fresh_body = _rename_clause(head, body)

        # 4b. Unificação do goal com a cabeça da regra.
        head_subst = unify(resolved_goal, fresh_head, subst)
        if head_subst is None:
            continue  # Cabeça não casa — próxima regra.

        # 4c. Resolução sequencial da conjunção do corpo.
        # Cada condição recebe todas as substituições produzidas pela anterior.
        current_substs: list[dict] = [head_subst]

        for condition in fresh_body:
            next_substs: list[dict] = []
            for s in current_substs:
                next_substs.extend(solve(condition, kb, s))
            current_substs = next_substs

            # Conjunção falhou: sem backtracking, descarta esta cláusula.
            if not current_substs:
                break

        yield from current_substs