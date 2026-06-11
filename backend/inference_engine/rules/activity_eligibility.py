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

from inference_engine.terms import Compound, Variable


def register(rule_base) -> None:
    atividade = Variable("Atividade")
    aluno = Variable("Aluno")

    rule_base.add_rule(
        Compound("atividade_elegivel", [atividade, aluno]),
        [
            Compound("dentro_periodo_curso", [atividade, aluno]),
            Compound("tem_comprovante", [atividade]),
            Compound("tipo_ativo", [atividade]),
            Compound("nao_excede_limite_categoria", [atividade, aluno]),
        ],
    )
