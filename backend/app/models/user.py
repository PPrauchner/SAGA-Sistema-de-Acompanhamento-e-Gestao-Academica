"""
Modelos Pydantic para a entidade User (perfil de usuário) e o fluxo de convite.

Responsabilidades:
- Definir UserBase com os campos comuns do perfil: uid, email, nome, role,
  programa_id, ativo.
- Definir UserResponse para o retorno de GET /api/v1/auth/me, acrescentando
  student_id ou advisor_id opcionais conforme o papel do usuário.
- Definir FirstAccessRequest (token + senha) para POST /api/v1/auth/first-access,
  validando a senha (mínimo 8 caracteres, 1 maiúscula, 1 número).
- Definir InviteRequest e InviteResponse para POST /api/v1/auth/invite.
- Mapear o documento Firestore da coleção users/{uid}, sincronizado com os
  custom claims do Firebase Auth (role, programa_id).

Referência: docs/specs/04_autenticacao.json (seção contratos_api).
"""

from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, Field, field_validator

# Papéis reconhecidos pelo sistema (custom claim 'role').
Role = Literal["aluno", "orientador", "coordenacao"]
# Convites só podem ser emitidos para aluno ou orientador — a coordenação
# não é criada por convite.
InviteRole = Literal["aluno", "orientador"]

# email-validator não faz parte das dependências do projeto; validação de
# formato é feita por expressão regular simples para evitar dependência extra.
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_PASSWORD_MIN_LEN = 8


def _normalizar_email(value: str) -> str:
    """Valida o formato e normaliza o e-mail (trim + minúsculas)."""
    value = value.strip()
    if not _EMAIL_RE.match(value):
        raise ValueError("E-mail em formato inválido")
    return value.lower()


class UserBase(BaseModel):
    """Campos comuns do perfil de usuário, espelhando users/{uid} no Firestore."""

    uid: str
    email: str
    nome: str
    role: Role
    programa_id: str
    ativo: bool = True

    @field_validator("email")
    @classmethod
    def _validar_email(cls, value: str) -> str:
        return _normalizar_email(value)


class UserResponse(UserBase):
    """Perfil retornado por GET /api/v1/auth/me."""

    student_id: str | None = None
    advisor_id: str | None = None


class FirstAccessRequest(BaseModel):
    """Corpo de POST /api/v1/auth/first-access: ativação de conta convidada."""

    token: str = Field(..., min_length=1)
    senha: str

    @field_validator("senha")
    @classmethod
    def _validar_senha(cls, value: str) -> str:
        if len(value) < _PASSWORD_MIN_LEN:
            raise ValueError("Senha deve ter no mínimo 8 caracteres")
        if not any(c.isupper() for c in value):
            raise ValueError("Senha deve conter ao menos 1 letra maiúscula")
        if not any(c.isdigit() for c in value):
            raise ValueError("Senha deve conter ao menos 1 número")
        return value


class InviteRequest(BaseModel):
    """Corpo de POST /api/v1/auth/invite: dados do convidado."""

    email: str
    role: InviteRole
    nome: str = Field(..., min_length=1)

    @field_validator("email")
    @classmethod
    def _validar_email(cls, value: str) -> str:
        return _normalizar_email(value)


class InviteResponse(BaseModel):
    """Resposta 201 de POST /api/v1/auth/invite."""

    message: str
    # UUID do convite — retornado apenas para testes; em produção só por e-mail.
    token: str
    expira_em: str  # ISO8601
