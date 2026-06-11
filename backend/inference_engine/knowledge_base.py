"""
Agregador de FactBase e RuleBase — interface única de consulta do motor de inferência.

Responsabilidades:
- FactBase: armazena fatos lógicos (Compounds) e os expõe ao resolver.
- RuleBase: armazena cláusulas (head, body) e as expõe ao resolver.
- InferenceEngine: ponto de entrada público — recebe uma FactBase e RuleBase e expõe
  query(goal) para execução de consultas sobre a base combinada.

Restrições:
- Sem imports de FastAPI, Firebase ou qualquer ORM.
- Único ponto de entrada externo: InferenceEngine.query(goal: Term) -> list[dict].
"""

from __future__ import annotations
from dataclasses import dataclass, field
from inference_engine.terms import Atom, Compound, Variable, Term
from inference_engine.substitution import apply as subst_apply
from inference_engine.resolver import solve


@dataclass
class Clause:
    head: Compound
    body: list[Compound] = field(default_factory=list)

    def __repr__(self) -> str:
        if not self.body:
            return repr(self.head)
        body_str = ", ".join(repr(c) for c in self.body)
        return f"{self.head!r} :- {body_str}"


class FactBase:
    """Repositório de fatos lógicos (Compounds) consultados pelo resolver."""

    def __init__(self) -> None:
        self._facts: list[Compound] = []

    def add_fact(self, compound: Compound) -> None:
        if not isinstance(compound, Compound):
            raise TypeError(f"Fato deve ser um Compound; recebido {type(compound).__name__}.")
        self._facts.append(compound)

    def get_facts(self) -> list[Compound]:
        return list(self._facts)

    def clear(self) -> None:
        self._facts.clear()

    def __len__(self) -> int:
        return len(self._facts)

    def __repr__(self) -> str:
        return f"FactBase({len(self._facts)} fato(s))"


class RuleBase:
    """Repositório de cláusulas lógicas (head :- body) consultadas pelo resolver."""

    def __init__(self) -> None:
        self._rules: list[Clause] = []

    def add_rule(self, head: Compound, body: list[Compound]) -> None:
        if not isinstance(head, Compound):
            raise TypeError(f"Head deve ser um Compound; recebido {type(head).__name__}.")
        self._rules.append(Clause(head=head, body=list(body)))

    def get_rules(self) -> list[tuple[Compound, list[Compound]]]:
        return [(clause.head, clause.body) for clause in self._rules]

    def clear(self) -> None:
        self._rules.clear()

    def __len__(self) -> int:
        return len(self._rules)

    def __repr__(self) -> str:
        return f"RuleBase({len(self._rules)} regra(s))"


class InferenceEngine:
    """Motor de inferência: ponto de entrada único para consultas lógicas.

    Attributes:
        fact_base: Base de fatos carregada pelo InferenceService antes de cada consulta.
        rule_base: Base de regras populada por register_all() com RL01-RL05.
    """

    def __init__(self, fact_base: FactBase, rule_base: RuleBase) -> None:
        self.fact_base = fact_base
        self.rule_base = rule_base

    def query(self, goal: Term) -> list[dict]:
        original_vars = self._collect_variable_names(goal)
        raw_results   = list(solve(goal, self, {}))

        if not original_vars:
            return raw_results

        clean_results: list[dict] = []
        for subst in raw_results:
            clean: dict[str, Term] = {}
            for var_name in original_vars:
                clean[var_name] = subst_apply(Variable(var_name), subst)
            clean_results.append(clean)

        return clean_results

    def _query_bool(self, goal: Term) -> bool:
        """
        Atalho interno para consultas booleanas.

        Retorna True se o goal tem ao menos uma solução, False caso contrário.
        Método privado — não faz parte da interface pública (spec §interface_única).
        Use query() externamente; _query_bool() é para uso interno e testes.
        """
        return next(solve(goal, self, {}), None) is not None

    def _collect_variable_names(self, term: Term) -> list[str]:
        if isinstance(term, Variable):
            return [term.name]
        if isinstance(term, Compound):
            names: list[str] = []
            for arg in term.args:
                names.extend(self._collect_variable_names(arg))
            return names
        return []

    def __repr__(self) -> str:
        return f"InferenceEngine({self.fact_base!r}, {self.rule_base!r})"