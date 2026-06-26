"""
Modelos Pydantic para o módulo de Prorrogações de Prazo.
Define o schema estrito do documento Firestore e os DTOs de entrada/saída.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class ExtensionStatus(str, Enum):
    PENDENTE  = "pendente"
    APROVADA  = "aprovada"
    REJEITADA = "rejeitada"


# ---------------------------------------------------------------------------
# Documento persistido no Firestore (schema canônico)
# ---------------------------------------------------------------------------

class ExtensionDocument(BaseModel):
    """Representa o documento completo na sub-coleção extensions."""

    aluno_id:              str
    motivo:                str = Field(..., min_length=10)
    plano_atualizado:      str
    parecer_orientador:    Optional[str]      = None
    semestres_solicitados: int
    status:                ExtensionStatus    = ExtensionStatus.PENDENTE
    prazo_novo:            Optional[datetime] = None
    aprovado_por:          Optional[str]      = None
    aprovado_em:           Optional[datetime] = None
    criado_em:             datetime

    @field_validator("semestres_solicitados")
    @classmethod
    def semestres_validos(cls, v: int) -> int:
        if v not in (1, 2):
            raise ValueError("semestres_solicitados deve ser 1 ou 2.")
        return v


# ---------------------------------------------------------------------------
# DTOs de entrada (request bodies)
# ---------------------------------------------------------------------------

class ExtensionCreateRequest(BaseModel):
    """Payload enviado pelo aluno ao criar uma solicitação."""

    motivo:                str = Field(..., min_length=10, description="Justificativa com no mínimo 10 caracteres.")
    plano_atualizado:      str = Field(..., description="Texto livre ou URL do comprovante/plano.")
    # M3: validação do teto máximo é feita dinamicamente no service (programs.max_prorrogacoes)
    # O validator local mantém apenas a rejeição de valores obviamente inválidos (≤ 0)
    semestres_solicitados: int = Field(..., gt=0, description="Quantidade de semestres solicitados.")


class ReviewRequest(BaseModel):
    """Payload enviado pelo orientador ao emitir parecer."""

    parecer_orientador: str = Field(..., min_length=10, description="Parecer técnico do orientador.")


class DecisionRequest(BaseModel):
    """Payload enviado pela coordenação ao deliberar."""

    aprovado: bool = Field(..., description="True para deferir, False para indeferir.")


# ---------------------------------------------------------------------------
# DTOs de saída (response bodies)
# ---------------------------------------------------------------------------

class ExtensionResponse(BaseModel):
    """Representação pública de uma prorrogação (retornada nos endpoints)."""

    # M2: frontend espera "id"; alias mantém compatibilidade com código interno que usa extension_id
    id:                    str            = Field(..., alias="extension_id")
    aluno_id:              str
    motivo:                str
    plano_atualizado:      str
    parecer_orientador:    Optional[str]
    semestres_solicitados: int
    status:                ExtensionStatus
    prazo_novo:            Optional[datetime]
    aprovado_por:          Optional[str]
    aprovado_em:           Optional[datetime]
    criado_em:             datetime

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)