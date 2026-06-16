"""
Agregador das regras declarativas RL01-RL05 do motor de inferência.

Responsabilidades:
- Importar os módulos de regra (defense_eligibility, credit_validation, academic_status,
  activity_eligibility, production_scoring).
- Expor register_all(rule_base): registra todas as cláusulas (head, body) de cada módulo
  na RuleBase fornecida.
- Único ponto de wiring das regras — adicionar uma nova regra significa criar o módulo,
  expor sua constante CLAUSES e incluí-lo em _RULE_MODULES.
- Módulo completamente isolado — sem imports de FastAPI, Firebase ou qualquer ORM.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from inference_engine.rules import (
    academic_status,
    activity_eligibility,
    credit_validation,
    defense_eligibility,
    production_scoring,
)

if TYPE_CHECKING:
    from inference_engine.knowledge_base import RuleBase

_RULE_MODULES = [
    defense_eligibility,
    credit_validation,
    academic_status,
    activity_eligibility,
    production_scoring,
]


def register_all(rule_base: "RuleBase") -> None:
    """Registra todas as cláusulas das regras RL01-RL05 na RuleBase fornecida.

    Args:
        rule_base: Instância de RuleBase a ser populada com as cláusulas (head, body)
            de cada módulo de regra.
    """
    for module in _RULE_MODULES:
        for head, body in module.CLAUSES:
            rule_base.add_rule(head, body)
