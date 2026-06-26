"""
Modelos Pydantic para a entidade Activity (atividade creditável).
Mapeia a sub-coleção Firestore students/{id}/activities.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Literal, Optional

from pydantic import BaseModel, Field, model_validator


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

    # None para atividades lastreadas em produção bibliográfica (ver producao_id);
    # obrigatório apenas na criação de atividades regulares (ActivityCreateRequest).
    tipo_id: str | None = None
    tipo_nome: Optional[str] = None
    categoria: Optional[str] = None

    # FK invertida para produção bibliográfica em coleção raiz (productions/{id}); None
    # para atividades regulares (não-bibliográficas).
    producao_id: str | None = None

    descricao: Optional[str] = None
    data_realizacao: datetime | None = None
    comprovante_url: Optional[str] = None

    creditos_gerados: float = 0.0
    creditos_concedidos: Optional[float] = None
    status: ActivityStatus | str = ActivityStatus.rascunho

    parecer_orientador: Optional[str] = None

    observacao_coordenacao: Optional[str] = None
    validado_por: Optional[str] = None
    validado_em: Optional[datetime] = None

    criado_em: Optional[datetime] = None
    atualizado_em: Optional[datetime] = None

    elegivel: Optional[bool] = None

    @model_validator(mode="before")
    @classmethod
    def _normalizar_campos_legados(cls, data: object) -> object:
        if not isinstance(data, dict):
            return data
        normalized = dict(data)
        if normalized.get("validado_por") is None and normalized.get("aprovado_por") is not None:
            normalized["validado_por"] = normalized["aprovado_por"]
        if normalized.get("validado_em") is None and normalized.get("aprovado_em") is not None:
            normalized["validado_em"] = normalized["aprovado_em"]
        return normalized


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
