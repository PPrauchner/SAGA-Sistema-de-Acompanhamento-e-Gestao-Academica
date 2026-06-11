"""
Modelos Pydantic de resposta para o endpoint de inferência lógica.

Responsabilidades:
- Definir InferenceResult, retorno de InferenceService.run_inference() e corpo da resposta
  de GET /api/v1/inference/{student_id}.
- Modelar o checklist resumido por item (status cumprido/pendente/em_risco), as atividades
  elegíveis (RL04), as pontuações ponderadas de produção (RL05) e a lista de fatos usados
  pelo motor — para exibição na InferencePage.
- Espelhar o contrato definido em docs/specs/01_motor_inferencia.json → contratos_api.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

RequisitoStatus = Literal["cumprido", "pendente", "em_risco"]
SituacaoInferida = Literal["regular", "em_risco", "qualificado", "fase_defesa"]


class CreditoMinimoItem(BaseModel):
    """Item de checklist de crédito com mínimo exigido."""

    status: RequisitoStatus
    obtidos: int
    minimo: int


class CreditoMaximoItem(BaseModel):
    """Item de checklist de crédito com máximo permitido (grupo tecnológico)."""

    status: RequisitoStatus
    obtidos: int
    maximo: int


class StatusItem(BaseModel):
    """Item de checklist booleano — apenas status (proficiência, qualificação etc.)."""

    status: RequisitoStatus


class InferenceChecklist(BaseModel):
    """Checklist resumido produzido pelo motor para a InferencePage."""

    creditos_minimos: CreditoMinimoItem
    creditos_grupo_basico: CreditoMinimoItem
    creditos_grupo_especifico: CreditoMinimoItem
    creditos_grupo_tecnologico: CreditoMaximoItem
    proficiencia: StatusItem
    qualificacao: StatusItem
    producao_validada: StatusItem
    plano_concluido: StatusItem


class PontuacaoProducao(BaseModel):
    """Pontuação ponderada de uma produção (resultado de RL05)."""

    producao_id: str
    score: float
    nivel_veiculo: str
    peso_aplicado: float


class InferenceResult(BaseModel):
    """Resultado completo da execução do motor de inferência para um aluno."""

    student_id: str
    programa_id: str
    timestamp: str
    situacao_inferida: SituacaoInferida
    apto_defesa: bool
    creditos_validos: bool
    em_risco: bool
    checklist: InferenceChecklist
    atividades_elegiveis: list[str]
    pontuacoes_producoes: list[PontuacaoProducao]
    fatos_usados: list[str]
    riscos_detectados: list[str] = []
    snapshot_id: str = ""
