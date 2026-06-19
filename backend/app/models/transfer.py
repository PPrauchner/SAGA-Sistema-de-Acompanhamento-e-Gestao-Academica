"""Modelos Pydantic para transferencia de orientandos entre orientadores."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel

TransferStatus = Literal["pendente", "aprovada", "cancelada"]
TransferTipo = Literal["direta_coordenacao", "solicitada_aluno"]


class DirectTransferRequest(BaseModel):
    student_id: str
    orientador_destino_id: str
    observacao: str | None = None


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
    observacao: str | None = None


class DirectTransferResponse(BaseModel):
    id: str
    student_id: str
    orientador_origem_id: str | None = None
    orientador_destino_id: str
    coorientador_limpo: bool
    pending_cancelled: bool
    message: str
