"""
Dependência FastAPI para autenticação e extração de identidade via Firebase Auth.

Responsabilidades:
- Definir o modelo CurrentUser com os campos uid, role, programa_id e email.
- Implementar a dependência assíncrona `get_current_user(authorization: str =
  Header(...)) -> CurrentUser` que:
    1. Extrai o Bearer token do header Authorization.
    2. Verifica o token com firebase_admin.auth.verify_id_token().
    3. Lê os custom claims 'role' e 'programa_id' do token decodificado.
    4. Lança HTTPException(401) para token ausente, inválido ou expirado.
    5. Lança HTTPException(403) se os custom claims estiverem ausentes
       (conta ainda não ativada via first-access).
- Ser a base sobre a qual o aspecto @requires_role (authorization.py) opera.

Referência: docs/specs/04_autenticacao.json (seção dependencia_fastapi).
"""

from __future__ import annotations

from fastapi import Header, HTTPException, status
from firebase_admin import auth as firebase_auth
from firebase_admin import exceptions as firebase_exceptions
from pydantic import BaseModel

from backend.app.models.user import Role

_BEARER_PREFIX = "Bearer "


class CurrentUser(BaseModel):
    """Identidade autenticada extraída do Firebase ID Token."""

    uid: str
    role: Role
    programa_id: str
    email: str | None = None


def _extrair_bearer_token(authorization: str) -> str:
    """Extrai o token do header 'Authorization: Bearer <token>'."""
    if not authorization.startswith(_BEARER_PREFIX):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Cabeçalho Authorization ausente ou mal formatado",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = authorization[len(_BEARER_PREFIX) :].strip()
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de autenticação ausente",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return token


async def get_current_user(
    authorization: str = Header(...),
) -> CurrentUser:
    """Verifica o Firebase ID Token e retorna a identidade do usuário atual."""
    token = _extrair_bearer_token(authorization)

    try:
        decoded = firebase_auth.verify_id_token(token)
    except (ValueError, firebase_exceptions.FirebaseError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido ou expirado",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    role = decoded.get("role")
    programa_id = decoded.get("programa_id")
    if not role or not programa_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Conta não ativada: custom claims ausentes no token",
        )

    return CurrentUser(
        uid=decoded["uid"],
        role=role,
        programa_id=programa_id,
        email=decoded.get("email"),
    )
