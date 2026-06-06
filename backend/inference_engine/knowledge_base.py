"""
Agregador de FactBase e RuleBase — interface única de consulta do motor de inferência.
knowledge_base.py
=================
Módulo   : Motor de Inferência Lógica
Versão   : 1.0.0-MVP
Spec     : docs/specs/01_motor_inferencia.json → modulos.knowledge_base.py

Responsabilidade
----------------
Agrega FactBase e RuleBase e expõe o InferenceEngine como único ponto de
acesso externo ao motor de inferência.

    engine = InferenceEngine(fact_base, rule_base)
    resultados = engine.query(goal)   # → list[dict]

O restante do sistema (FastAPI, InferenceService, testes) nunca importa
FactBase, RuleBase ou solver diretamente — apenas InferenceEngine.

Componentes (spec §knowledge_base.py.componentes)
-------------------------------------------------
FactBase
    Coleção de Compounds verdadeiros. Populada pelo InferenceService
    antes de cada consulta, a partir dos dados do Firestore.
    Métodos públicos: add_fact(compound), get_facts(), clear().

RuleBase
    Coleção de cláusulas (head: Compound, body: list[Compound]).
    Importadas dos módulos em rules/ via rules.register_all(rule_base).
    Alterar uma política acadêmica = alterar o módulo de regra correspondente,
    não o fluxo de controle desta classe.
    Métodos públicos: add_rule(head, body), get_rules(), clear().

InferenceEngine
    Orquestra FactBase + RuleBase + solve().
    Interface pública única: query(goal) → list[dict].
    O método query() filtra o resultado para expor apenas as variáveis
    presentes no goal original, descartando variáveis internas de renaming.

Dependências internas
---------------------
  inference_engine.terms    — Compound, Variable, Term
  inference_engine.resolver — solve()

Dependências externas
---------------------
  NENHUMA — módulo completamente isolado de FastAPI e Firebase.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from inference_engine.terms import Atom, Compound, Variable, Term
from inference_engine.substitution import apply as subst_apply
from inference_engine.resolver import solve


# ---------------------------------------------------------------------------
# Clause — tipo auxiliar interno
# ---------------------------------------------------------------------------

@dataclass
class Clause:
    """
    Representa uma cláusula lógica: head é verdadeiro se todos os termos
    de body forem verdadeiros (conjunção).

    Usada internamente pela RuleBase; não é parte da interface pública.

    Exemplo de representação textual:
        apto_defesa(A) :- creditos_validos(A), qualificacao_aprovada(A), ...
    """
    head: Compound
    body: list[Compound] = field(default_factory=list)

    def __repr__(self) -> str:
        if not self.body:
            return repr(self.head)
        body_str = ", ".join(repr(c) for c in self.body)
        return f"{self.head!r} :- {body_str}"


# ---------------------------------------------------------------------------
# FactBase
# ---------------------------------------------------------------------------

class FactBase:
    """
    Coleção de fatos concretos do domínio acadêmico.

    Fatos são Compounds sem variáveis — afirmações que o motor considera
    verdadeiras durante uma consulta. Exemplos:

        creditos_validos('aluno_001')
        qualificacao_aprovada('aluno_001')
        nivel_relevancia('veiculo_42', 'prog_default', 'A1')

    Ciclo de vida por consulta
    --------------------------
    O InferenceService (backend/app/services/inference_service.py) é o único
    responsável por popular a FactBase. O fluxo típico é:

        1. InferenceService carrega dados do Firestore para o aluno solicitado.
        2. Converte os dados em Compounds e chama add_fact() para cada um.
        3. Passa a FactBase populada ao InferenceEngine.
        4. Após a consulta, pode chamar clear() para reutilizar a instância.
    """

    def __init__(self) -> None:
        self._facts: list[Compound] = []

    def add_fact(self, compound: Compound) -> None:
        """
        Registra um fato concreto na base.

        Parâmetros
        ----------
        compound : Compound
            Fato a registrar. Deve ser um Compound (não Variable nem Atom solto).

        Raises
        ------
        TypeError : se compound não for uma instância de Compound.
        """
        if not isinstance(compound, Compound):
            raise TypeError(
                f"Fato deve ser um Compound; recebido {type(compound).__name__}."
            )
        self._facts.append(compound)

    def get_facts(self) -> list[Compound]:
        """
        Retorna cópia da lista de fatos.

        O resolver itera sobre esta lista; a cópia evita que modificações
        concorrentes durante a iteração causem comportamento indefinido.
        """
        return list(self._facts)

    def clear(self) -> None:
        """Remove todos os fatos — útil para reutilizar a instância entre consultas."""
        self._facts.clear()

    def __len__(self) -> int:
        return len(self._facts)

    def __repr__(self) -> str:
        return f"FactBase({len(self._facts)} fato(s))"


# ---------------------------------------------------------------------------
# RuleBase
# ---------------------------------------------------------------------------

class RuleBase:
    """
    Coleção de cláusulas (regras) que expressam as políticas acadêmicas do programa.

    Cada módulo em inference_engine/rules/ expõe uma função register(rule_base)
    que adiciona suas cláusulas. Alterar uma política = alterar o módulo de regra,
    nunca o código desta classe nem o fluxo de controle do resolver.

    Regras registradas (via rules/__init__.py → register_all)
    ---------------------------------------------------------
    RL01  defense_eligibility.py   apto_defesa(A)
    RL02  credit_validation.py     creditos_validos(A)
    RL03  academic_status.py       em_risco(A)          [4 cláusulas OR]
    RL04  activity_eligibility.py  atividade_elegivel(Atv, A)
    RL05  production_scoring.py    pontuacao_producao(P, Score)
    """

    def __init__(self) -> None:
        self._rules: list[Clause] = []

    def add_rule(self, head: Compound, body: list[Compound]) -> None:
        """
        Registra uma cláusula na base de regras.

        Parâmetros
        ----------
        head : Compound
            Conclusão da regra (ex: Compound('apto_defesa', [Variable('A')])).
        body : list[Compound]
            Condições que devem ser satisfeitas para provar head.
            Lista vazia = fato implícito (sem condições).

        Raises
        ------
        TypeError : se head não for um Compound.
        """
        if not isinstance(head, Compound):
            raise TypeError(
                f"Head deve ser um Compound; recebido {type(head).__name__}."
            )
        self._rules.append(Clause(head=head, body=list(body)))

    def get_rules(self) -> list[tuple[Compound, list[Compound]]]:
        """
        Retorna lista de (head, body) para consumo pelo resolver.

        O resolver nunca acessa _rules diretamente — passa sempre por este método.
        """
        return [(clause.head, clause.body) for clause in self._rules]

    def clear(self) -> None:
        """Remove todas as regras."""
        self._rules.clear()

    def __len__(self) -> int:
        return len(self._rules)

    def __repr__(self) -> str:
        return f"RuleBase({len(self._rules)} regra(s))"


# ---------------------------------------------------------------------------
# InferenceEngine — interface pública única do motor
# ---------------------------------------------------------------------------

class InferenceEngine:
    """
    Orquestra FactBase + RuleBase + solve().

    É o único objeto que o restante do sistema (InferenceService, endpoints,
    testes de integração) conhece do motor de inferência. Nenhum outro módulo
    deste pacote deve ser importado fora de inference_engine/.

    Uso padrão (InferenceService)
    -----------------------------
        fb = FactBase()
        rb = RuleBase()
        # ... InferenceService popula fb com fatos do Firestore ...
        register_all(rb)
        engine = InferenceEngine(fb, rb)

        apto   = engine.query_bool(Compound('apto_defesa',   [Atom(student_id)]))
        risco  = engine.query_bool(Compound('em_risco',      [Atom(student_id)]))
        scores = engine.query(Compound('pontuacao_producao', [Variable('P'), Variable('Score')]))

    Filtragem de variáveis internas
    --------------------------------
    O resolver renomeia variáveis de cláusulas com sufixos (ex: A_7) para evitar
    colisões. query() coleta as variáveis do goal original e resolve apenas elas
    na substituição final, descartando as variáveis internas de renaming.
    Isso garante que o chamador receba {'Score': Atom(20.0)}, não {'Score_7': ...}.
    """

    def __init__(self, fact_base: FactBase, rule_base: RuleBase) -> None:
        self.fact_base = fact_base
        self.rule_base = rule_base

    # ------------------------------------------------------------------
    # Interface pública
    # ------------------------------------------------------------------

    def query(self, goal: Term) -> list[dict]:
        """
        Executa uma consulta contra a base de conhecimento.

        Parâmetros
        ----------
        goal : Term
            Predicado a provar. Geralmente um Compound, podendo conter Variables
            para consultas que retornam valores (ex: pontuacao_producao).

        Retorna
        -------
        list[dict[str, Term]]
            Uma entrada por solução encontrada. Cada dict mapeia o nome das
            variáveis do goal original para os valores resolvidos.
            Lista vazia = goal não provável com a base atual.

        Exemplos
        --------
        # Consulta booleana (sem variáveis no goal)
        results = engine.query(Compound('apto_defesa', [Atom('aluno_001')]))
        apto = len(results) > 0

        # Consulta com variável
        results = engine.query(Compound('pontuacao_producao', [Atom('p1'), Variable('Score')]))
        score = results[0]['Score'].value  # ex: 20.0
        """
        original_vars = self._collect_variable_names(goal)
        raw_results   = list(solve(goal, self, {}))

        # Se o goal não continha variáveis, retorna as substituições brutas
        # (dicts vazios) para indicar apenas sucesso/falha.
        if not original_vars:
            return raw_results

        # Filtra e resolve apenas as variáveis do goal original.
        clean_results: list[dict] = []
        for subst in raw_results:
            clean: dict[str, Term] = {}
            for var_name in original_vars:
                clean[var_name] = subst_apply(Variable(var_name), subst)
            clean_results.append(clean)

        return clean_results

    def query_bool(self, goal: Term) -> bool:
        """
        Atalho para consultas booleanas.

        Retorna True se o goal tem ao menos uma solução, False caso contrário.
        Preferível a len(query(...)) > 0 quando o chamador não precisa das substituições.
        """
        # Usa next() sobre o generator de solve() para evitar computar todas
        # as soluções quando apenas a existência importa.
        return next(solve(goal, self, {}), None) is not None

    # ------------------------------------------------------------------
    # Métodos auxiliares privados
    # ------------------------------------------------------------------

    def _collect_variable_names(self, term: Term) -> list[str]:
        """
        Percorre um termo recursivamente e retorna os nomes de todas as
        Variables encontradas, na ordem em que aparecem.

        Usado por query() para filtrar a substituição final.
        """
        if isinstance(term, Variable):
            return [term.name]
        if isinstance(term, Compound):
            names: list[str] = []
            for arg in term.args:
                names.extend(self._collect_variable_names(arg))
            return names
        return []  # Atom: sem variáveis

    def __repr__(self) -> str:
        return f"InferenceEngine({self.fact_base!r}, {self.rule_base!r})"
