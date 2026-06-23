"""Schemas Pydantic para transferencia cross-program."""

from __future__ import annotations

from pydantic import BaseModel, Field


class TransferCrossCreateRequest(BaseModel):
    """Payload de criacao de solicitacao cross-program."""

    student_id: str = Field(..., description="ID do discente a ser transferido")
    orientador_destino_id: str = Field(..., description="ID do orientador receptor")
    programa_destino_id: str = Field(..., description="ID do programa de destino")
    motivo: str = Field(..., min_length=5, description="Justificativa da solicitacao")


class TransferCrossRejectRequest(BaseModel):
    """Payload de rejeicao de solicitacao cross-program."""

    motivo: str = Field(..., min_length=5, description="Motivo obrigatorio da rejeicao")