"""Modelos Pydantic para solicitacoes de prorrogacao."""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field

from backend.app.models.validators import DataFutura

ExtensionStatus = Literal["pendente", "em_analise", "aprovada", "rejeitada"]
ExtensionType = Literal[
    "prazo_defesa", "prazo_qualificacao", "trancamento", "mudanca_nivel"
]


class ExtensionCreateRequest(BaseModel):
    tipo: ExtensionType
    nova_data: DataFutura
    motivo: str = Field(..., min_length=1)
    student_id: str | None = None


class ExtensionRejectRequest(BaseModel):
    motivo: str = Field(..., min_length=1)


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
