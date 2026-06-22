"""Modelos Pydantic para transferencia de orientandos entre orientadores."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel

TransferStatus = Literal["pendente", "aprovada", "rejeitada", "cancelada"]
TransferTipo = Literal["direta_coordenacao", "solicitada_orientador", "solicitada_aluno"]


class DirectTransferRequest(BaseModel):
    student_id: str
    orientador_destino_id: str
    observacao: str | None = None


class TransferCreateRequest(BaseModel):
    student_id: str
    orientador_destino_id: str
    motivo: str | None = None


class TransferRejectRequest(BaseModel):
    motivo: str


class TransferRequestResponse(BaseModel):
    id: str
    student_id: str
    orientador_origem_id: str | None = None
    orientador_destino_id: str
    status: TransferStatus
    tipo: TransferTipo
    solicitante_id: str
    programa_id: str
    created_at: datetime
    updated_at: datetime
    cancelled_at: datetime | None = None
    cancelado_em: datetime | None = None
    decidido_por: str | None = None
    decidido_em: datetime | None = None
    motivo: str | None = None
    observacao: str | None = None


class DirectTransferResponse(BaseModel):
    id: str
    student_id: str
    orientador_origem_id: str | None = None
    orientador_destino_id: str
    coorientador_limpo: bool
    pending_cancelled: bool
    message: str
