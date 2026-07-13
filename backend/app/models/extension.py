"""
Modelos Pydantic para o módulo de Prorrogações de Prazo (extensions).

Responsabilidades:
- Definir o schema do documento persistido na coleção raiz `extensions/`
  (ADR-0006), alinhado a docs/data-model.md §4 e docs/specs/03_firebase_schema.json.
- Definir os DTOs de entrada (solicitação, parecer, decisão) e de saída.

Fluxo orientado a data (data-model §4): o aluno informa `nova_data` (novo prazo
pretendido); `semestres_solicitados` é campo legado e não faz parte deste modelo.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

from backend.app.models.validators import DataFutura


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class ExtensionStatus(str, Enum):
    """Estados do ciclo de vida de uma prorrogação (data-model §4)."""

    PENDENTE   = "pendente"
    EM_ANALISE = "em_analise"
    APROVADA   = "aprovada"
    REJEITADA  = "rejeitada"


class ExtensionTipo(str, Enum):
    """Natureza da solicitação de prorrogação (03_firebase_schema.json)."""

    PRAZO_DEFESA       = "prazo_defesa"
    PRAZO_QUALIFICACAO = "prazo_qualificacao"
    TRANCAMENTO        = "trancamento"
    MUDANCA_NIVEL      = "mudanca_nivel"


# ---------------------------------------------------------------------------
# Documento persistido no Firestore (coleção raiz `extensions/`)
# ---------------------------------------------------------------------------

class ExtensionDocument(BaseModel):
    """Representa o documento completo da coleção raiz `extensions/`.

    Attributes:
        student_id: Doc id do aluno em `students/` (auto-id, não uid).
        requester_id: uid de quem abriu a solicitação.
        programa_id: Discriminador de tenant, derivado do aluno.
        tipo: Natureza da prorrogação.
        motivo: Justificativa do aluno.
        plano_atualizado: Descrição/URL do plano de trabalho revisado.
        parecer_orientador: Parecer técnico do orientador (campo, não estado).
        observacao_coordenacao: Observação registrada pela coordenação ao deliberar.
        status: Estado atual do ciclo de vida.
        nova_data: Novo prazo pretendido, informado pelo aluno.
        data_atual: `prazo_final` vigente do aluno no momento da solicitação.
        prazo_novo: Snapshot do prazo concedido (preenchido na aprovação).
        aprovado_por: uid da coordenação que aprovou.
        aprovado_em: Momento da aprovação.
        motivo_rejeicao: Justificativa obrigatória da coordenação ao rejeitar.
        rejeitado_por: uid da coordenação que rejeitou.
        rejeitado_em: Momento da rejeição.
        created_at: Momento da criação da solicitação.
    """

    student_id:             str
    requester_id:           str
    programa_id:            str | None = None
    tipo:                   ExtensionTipo
    motivo:                 str = Field(..., min_length=10)
    plano_atualizado:       str
    parecer_orientador:     str | None = None
    observacao_coordenacao: str | None = None
    status:                 ExtensionStatus = ExtensionStatus.PENDENTE
    nova_data:              datetime
    data_atual:             datetime | None = None
    prazo_novo:             datetime | None = None
    aprovado_por:           str | None = None
    aprovado_em:            datetime | None = None
    motivo_rejeicao:        str | None = None
    rejeitado_por:          str | None = None
    rejeitado_em:           datetime | None = None
    created_at:             datetime


# ---------------------------------------------------------------------------
# DTOs de entrada (request bodies)
# ---------------------------------------------------------------------------

class ExtensionCreateRequest(BaseModel):
    """Payload enviado pelo aluno ao solicitar uma prorrogação."""

    tipo:             ExtensionTipo = Field(..., description="Natureza da prorrogação solicitada.")
    motivo:           str = Field(..., min_length=10, description="Justificativa (mínimo 10 caracteres).")
    plano_atualizado: str = Field(..., min_length=1, description="Descrição ou URL do plano de trabalho revisado.")
    nova_data:        DataFutura = Field(..., description="Novo prazo pretendido pelo aluno.")


class ReviewRequest(BaseModel):
    """Payload enviado pelo orientador ao emitir parecer."""

    parecer_orientador: str = Field(..., min_length=10, description="Parecer técnico do orientador.")


class ApproveRequest(BaseModel):
    """Payload enviado pela coordenação ao aprovar (Spec 08 — POST /approve).

    A Spec 08 não exige corpo na aprovação; `observacao` é opcional para que a
    coordenação possa registrar a justificativa do deferimento.
    """

    observacao: str | None = Field(None, description="Observação opcional da coordenação.")


class RejectRequest(BaseModel):
    """Payload enviado pela coordenação ao rejeitar (Spec 08 — POST /reject)."""

    motivo: str = Field(..., min_length=1, description="Justificativa da rejeição (obrigatória).")


# ---------------------------------------------------------------------------
# DTO de saída (response body)
# ---------------------------------------------------------------------------

class ExtensionResponse(BaseModel):
    """Representação pública de uma prorrogação retornada pelos endpoints."""

    id:                     str
    student_id:             str
    requester_id:           str
    programa_id:            str | None = None
    tipo:                   ExtensionTipo
    motivo:                 str
    plano_atualizado:       str
    parecer_orientador:     str | None = None
    observacao_coordenacao: str | None = None
    status:                 ExtensionStatus
    nova_data:              datetime
    data_atual:             datetime | None = None
    prazo_novo:             datetime | None = None
    aprovado_por:           str | None = None
    aprovado_em:            datetime | None = None
    motivo_rejeicao:        str | None = None
    rejeitado_por:          str | None = None
    rejeitado_em:           datetime | None = None
    created_at:             datetime
    # Enriquecidos pelo service nas listagens, a partir do aluno referenciado por
    # student_id. Ausentes na resposta de criação (não há listagem a enriquecer).
    student_nome:           str | None = None
    matricula:              str | None = None
    nivel:                  str | None = None

    model_config = ConfigDict(from_attributes=True)
