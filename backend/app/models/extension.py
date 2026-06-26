<<<<<<< HEAD
"""
Modelos Pydantic para o módulo de Prorrogações de Prazo.
Define o schema estrito do documento Firestore e os DTOs de entrada/saída.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator


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

    aluno_id:             str
    motivo:               str = Field(..., min_length=10)
    plano_atualizado:     str
    parecer_orientador:   Optional[str]  = None
    semestres_solicitados: int
    status:               ExtensionStatus = ExtensionStatus.PENDENTE
    prazo_novo:           Optional[datetime] = None
    aprovado_por:         Optional[str]  = None
    aprovado_em:          Optional[datetime] = None
    criado_em:            datetime

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

    motivo:               str = Field(..., min_length=10, description="Justificativa com no mínimo 10 caracteres.")
    plano_atualizado:     str = Field(..., description="Texto livre ou URL do comprovante/plano.")
    semestres_solicitados: int = Field(..., description="Quantidade de semestres solicitados (1 ou 2).")

    @field_validator("semestres_solicitados")
    @classmethod
    def semestres_validos(cls, v: int) -> int:
        if v not in (1, 2):
            raise ValueError("semestres_solicitados deve ser 1 ou 2.")
        return v


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

    extension_id:          str
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

    model_config = {"from_attributes": True}
=======
"""Modelos Pydantic para solicitacoes de prorrogacao."""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field

ExtensionStatus = Literal["pendente", "em_analise", "aprovada", "rejeitada"]


class ExtensionCreateRequest(BaseModel):
    tipo: str = "prazo_defesa"
    nova_data: date
    motivo: str = Field(..., min_length=1)
    student_id: str | None = None


class ExtensionResponse(BaseModel):
    id: str
    tipo: str
    status: ExtensionStatus | str
    student_id: str
    aluno_id: str
    aluno_nome: str
    aluno: str
    matricula: str | None = None
    nivel: str | None = None
    nova_data: date | None = None
    prazo_novo: date | None = None
    data_atual: date | None = None
    prazo_atual: date | None = None
    created_at: datetime
    solicitacao: datetime
    motivo: str
    justificativa: str
    parecer: str | None = None
>>>>>>> 0161ba8854c4238232217a8a4715b9d5484d34b9
