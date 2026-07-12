"""
Modelos Pydantic de resposta para o checklist de integralização.

Responsabilidades:
- Definir ChecklistResponse, retorno de ChecklistService.get_checklist() e corpo da resposta
  de GET /api/v1/checklist/{student_id}.
- Modelar os 8 requisitos de integralização (créditos mínimos totais, créditos por grupo
  básico, específico e tecnológico, proficiência, qualificação, produção validada, plano
  concluído), cada um com status cumprido/pendente/em_risco e valores reais.
- Carregar a flag conflito_situacao (situacao_registrada != situacao_inferida), a lista de
  riscos detectados (RL03) e o id do snapshot persistido em inferred_status/.
- Espelhar o contrato definido em docs/specs/08_checklist_prorrogacoes.json → contratos_api.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

RequisitoStatus = Literal["cumprido", "pendente", "em_risco"]


class CreditoMinimoRequisito(BaseModel):
    """Requisito de crédito com mínimo exigido (total, básico, específico)."""

    status: RequisitoStatus
    obtidos: float
    minimo: float
    descricao: str


class CreditoMaximoRequisito(BaseModel):
    """Requisito de crédito com máximo permitido (grupo tecnológico)."""

    status: RequisitoStatus
    obtidos: float
    maximo: float
    descricao: str


class ProficienciaRequisito(BaseModel):
    """Requisito de proficiência em língua estrangeira."""

    status: RequisitoStatus
    data_comprovacao: str | None = None
    comprovante_url: str | None = None


class QualificacaoRequisito(BaseModel):
    """Requisito de aprovação no exame de qualificação."""

    status: RequisitoStatus
    data_aprovacao: str | None = None
    comprovante_url: str | None = None


class ProducaoRequisito(BaseModel):
    """Requisito de produção bibliográfica validada."""

    status: RequisitoStatus
    quantidade_aprovadas: int


class PlanoRequisito(BaseModel):
    """Requisito de conclusão do plano de trabalho (etapas não-defesa)."""

    status: RequisitoStatus
    tasks_concluidas: int
    tasks_total_nao_defesa: int


class ChecklistRequisitos(BaseModel):
    """Agregação dos 7 requisitos de integralização."""

    creditos_minimos: CreditoMinimoRequisito
    creditos_grupo_basico: CreditoMinimoRequisito
    creditos_grupo_especifico: CreditoMinimoRequisito
    creditos_grupo_tecnologico: CreditoMaximoRequisito
    proficiencia: ProficienciaRequisito
    qualificacao: QualificacaoRequisito
    producao_validada: ProducaoRequisito
    plano_concluido: PlanoRequisito


class ChecklistResponse(BaseModel):
    """Resposta completa do checklist de integralização de um aluno."""

    student_id: str
    student_nome: str
    timestamp: str
    situacao_registrada: str
    situacao_inferida: str
    conflito_situacao: bool
    apto_defesa: bool
    requisitos: ChecklistRequisitos
    riscos_detectados: list[str]
    snapshot_id: str
