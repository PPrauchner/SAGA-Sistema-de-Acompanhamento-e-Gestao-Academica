"""
Ponto de entrada das regras acadêmicas do motor de inferência.

Exporta register_all() que registra RL01–RL05 em uma RuleBase.
"""

from __future__ import annotations

from inference_engine.knowledge_base import RuleBase
from inference_engine.rules import (
    academic_status,
    activity_eligibility,
    credit_validation,
    defense_eligibility,
    production_scoring,
)


def register_all(rb: RuleBase) -> None:
    """Registra todas as regras acadêmicas (RL01–RL05) na RuleBase.

    Args:
        rb: RuleBase que receberá as cláusulas.
    """
    defense_eligibility.register(rb)
    credit_validation.register(rb)
    academic_status.register(rb)
    activity_eligibility.register(rb)
    production_scoring.register(rb)
