"""Modelos Pydantic para solicitações públicas de cadastro."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator

from backend.app.models.student import StudentLevel

RegistrationRequestStatus = Literal["pendente", "aprovado", "rejeitado"]


class RegistrationRequestCreate(BaseModel):
    nome: str
    email: str
    orientador_id: str = Field(
        validation_alias=AliasChoices("orientador_id", "advisor_id"),
    )

    model_config = ConfigDict(populate_by_name=True)

    @field_validator("nome", "email", "orientador_id")
    @classmethod
    def _required(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Campo obrigatorio")
        return value

    @field_validator("email")
    @classmethod
    def _normalize_email(cls, value: str) -> str:
        normalized = value.strip().lower()
        if "@" not in normalized or "." not in normalized.rsplit("@", 1)[-1]:
            raise ValueError("E-mail invalido")
        return normalized


class RegistrationRequestApprove(BaseModel):
    matricula: str | None = None
    nivel: StudentLevel = "mestrado"
    data_ingresso: datetime | None = None


class RegistrationRequestReject(BaseModel):
    motivo: str | None = None


class RegistrationRequestResponse(BaseModel):
    id: str
    nome: str
    email: str
    orientador_id: str
    programa_id: str
    status: RegistrationRequestStatus
    created_at: datetime
    reviewed_by: str | None = None
    reviewed_at: datetime | None = None
    orientador_nome: str | None = None
    student_id: str | None = None
    invite_token: str | None = None
    rejection_reason: str | None = None
