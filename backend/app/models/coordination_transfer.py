"""Modelos do fluxo de transferencia de coordenacao."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

CoordinationTransferStatus = Literal["pendente", "aceita", "rejeitada", "cancelada"]


class CoordinationTransferStartRequest(BaseModel):
    successor_uid: str = Field(..., min_length=1)


class CoordinationTransferActionResponse(BaseModel):
    message: str
    id: str
    programa_id: str
    initiator_uid: str
    successor_uid: str
    status: CoordinationTransferStatus


class CoordinationTransferResponse(BaseModel):
    id: str
    programa_id: str
    initiator_uid: str
    successor_uid: str
    status: CoordinationTransferStatus
    created_at: datetime
    updated_at: datetime
    decided_at: datetime | None = None
    cancelled_at: datetime | None = None
    rejected_at: datetime | None = None
    accepted_at: datetime | None = None
    rejected_by: str | None = None
    cancelled_by: str | None = None
