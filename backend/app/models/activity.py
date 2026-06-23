"""
Modelos Pydantic para a entidade Activity (atividade creditável).
Mapeia a sub-coleção Firestore students/{id}/activities.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Literal, Optional

from pydantic import BaseModel, Field


class ActivityStatus(str, Enum):
    rascunho = "rascunho"
    enviado = "enviado"
    aprovado = "aprovado"
    rejeitado = "rejeitado"


ActivityCreateStatus = Literal["rascunho", "enviado"]


class ValidateAction(str, Enum):
    aprovar = "aprovar"
    rejeitar = "rejeitar"


class ActivityCreateRequest(BaseModel):
    tipo_id: str
    descricao: str
    data_realizacao: datetime
    comprovante_url: str | None = None
    status: ActivityCreateStatus = "enviado"


class ActivityCreateResponse(BaseModel):
    id: str
    elegibilidade_preliminar: bool
    notificacao_enviada: bool


class ActivityResponse(BaseModel):
    id: str
    student_id: Optional[str] = None

    tipo_id: str
    tipo_nome: Optional[str] = None
    categoria: Optional[str] = None

    descricao: Optional[str] = None
    data_realizacao: datetime | None = None
    comprovante_url: Optional[str] = None

    creditos_gerados: float = 0.0
    status: ActivityStatus | str = ActivityStatus.rascunho

    parecer_orientador: Optional[str] = None

    observacao_coordenacao: Optional[str] = None
    aprovado_por: Optional[str] = None
    aprovado_em: Optional[datetime] = None

    criado_em: Optional[datetime] = None
    atualizado_em: Optional[datetime] = None

    elegivel: Optional[bool] = None


class ParecerRequest(BaseModel):
    """Corpo de PATCH /activities/{id}/parecer — parecer textual do orientador."""

    parecer: str = Field(..., min_length=1, description="Texto do parecer do orientador")


class ValidateActivityRequest(BaseModel):
    acao: ValidateAction
    observacao: Optional[str] = Field(default=None)
    creditos_concedidos: Optional[float] = Field(default=None)


class ValidateActivityResponse(BaseModel):
    message: str
    novo_status: ActivityStatus
    creditos_contabilizados: Optional[float] = None
    motor_inferencia_executado: bool = False
    fato_gerado: Optional[str] = None


class ComprovanteUploadResponse(BaseModel):
    comprovante_url: str
    path_bucket: str