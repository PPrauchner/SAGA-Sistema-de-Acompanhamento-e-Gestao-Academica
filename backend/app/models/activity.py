"""
Modelos Pydantic para a entidade Activity (atividade creditável).
Mapeia a sub-coleção Firestore students/{id}/activities.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Literal

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


class ActivityCreateByAdvisorRequest(BaseModel):
    """Corpo de POST /activities/orientador — orientador cria atividade para um orientando.

    A criação pelo orientador já é o endosso: a atividade nasce em `enviado` com o parecer
    preenchido, sem passo separado de parecer (não há status a escolher).
    """

    aluno_id: str
    tipo_id: str
    descricao: str
    data_realizacao: datetime
    comprovante_url: str | None = None
    parecer: str = Field(..., min_length=1, description="Parecer/endosso do orientador")


class ActivityCreateResponse(BaseModel):
    id: str
    elegibilidade_preliminar: bool
    notificacao_enviada: bool


class ActivityResponse(BaseModel):
    id: str
    student_id: str | None = None
    aluno_nome: str | None = None
    orientador_nome: str | None = None

    # None para atividades lastreadas em produção bibliográfica (ver producao_id);
    # obrigatório apenas na criação de atividades regulares (ActivityCreateRequest).
    tipo_id: str | None = None
    tipo_nome: str | None = None
    categoria: str | None = None

    # FK invertida para produção bibliográfica em coleção raiz (productions/{id}); None
    # para atividades regulares (não-bibliográficas).
    producao_id: str | None = None

    descricao: str | None = None
    data_realizacao: datetime | None = None
    comprovante_url: str | None = None

    creditos_gerados: float = 0.0
    creditos_concedidos: float | None = None
    status: ActivityStatus | str = ActivityStatus.rascunho

    parecer_orientador: str | None = None

    observacao_coordenacao: str | None = None
    validado_por: str | None = None
    validado_em: datetime | None = None

    criado_em: datetime | None = None
    atualizado_em: datetime | None = None

    elegivel: bool | None = None

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
    observacao: str | None = Field(default=None)
    creditos_concedidos: float | None = Field(default=None)


class ValidateActivityResponse(BaseModel):
    message: str
    novo_status: ActivityStatus
    creditos_contabilizados: float | None = None
    motor_inferencia_executado: bool = False
    fato_gerado: str | None = None


class ComprovanteUploadResponse(BaseModel):
    comprovante_url: str
    path_bucket: str
