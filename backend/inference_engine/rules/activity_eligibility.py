"""
Regra RL04 — Elegibilidade de Atividade Creditável (declarativa).

Responsabilidades:
- Declarar a cláusula: atividade_elegivel(Atv, A) :- dentro_periodo_curso(Atv, A),
  tem_comprovante(Atv), tipo_ativo(Atv), nao_excede_limite_categoria(Atv, A).
- Todas as 4 condições devem ser satisfeitas para a atividade ser contabilizada.
- nao_excede_limite_categoria é verificação positiva: InferenceService pré-calcula soma
  de créditos aprovados da categoria e insere o fato positivo se abaixo do limite.
- Executada em ActivityService.submit_activity() (elegibilidade preliminar) e em
  ActivityService.validate_activity() (verificação definitiva antes de contabilizar créditos).
- Casos de teste: elegivel (4 fatos presentes), sem_comprovante, tipo_inativo,
  excede_limite_tecnologico.
"""

from __future__ import annotations

from inference_engine.terms import Variable, Compound
from inference_engine.knowledge_base import RuleBase


def register(rb: RuleBase) -> None:
    """Registra RL04 na RuleBase fornecida.

    Args:
        rb: RuleBase onde a regra será adicionada.
    """
    Atv = Variable("Atv")
    A   = Variable("A")

    head = Compound("atividade_elegivel", [Atv, A])
    body = [
        Compound("dentro_periodo_curso",       [Atv, A]),
        Compound("tem_comprovante",             [Atv]),
        Compound("tipo_ativo",                  [Atv]),
        Compound("nao_excede_limite_categoria", [Atv, A]),
    ]
    rb.add_rule(head, body)
