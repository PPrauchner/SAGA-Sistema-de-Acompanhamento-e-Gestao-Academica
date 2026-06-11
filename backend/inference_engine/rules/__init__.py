from inference_engine.rules.academic_status import register as register_academic_status
from inference_engine.rules.activity_eligibility import (
    register as register_activity_eligibility,
)
from inference_engine.rules.credit_validation import (
    register as register_credit_validation,
)
from inference_engine.rules.defense_eligibility import (
    register as register_defense_eligibility,
)
from inference_engine.rules.production_scoring import (
    register as register_production_scoring,
)


def register_all(rule_base) -> None:
    register_defense_eligibility(rule_base)
    register_credit_validation(rule_base)
    register_academic_status(rule_base)
    register_activity_eligibility(rule_base)
    register_production_scoring(rule_base)
