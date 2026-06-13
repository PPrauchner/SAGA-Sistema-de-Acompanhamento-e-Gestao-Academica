"""
Dependência FastAPI para autenticação via Firebase Auth.

Responsabilidades:
- Definir CurrentUser com uid, role, programa_id, email.
- Implementar get_current_user() que verifica o token JWT e extrai custom claims.
"""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import Header, HTTPException, status
from firebase_admin import auth

from backend.app.core.firebase import init_firebase


@dataclass
class CurrentUser:
    """Usuário autenticado extraído do token JWT Firebase."""

    uid: str
    role: str
    programa_id: str
    email: str


async def get_current_user(authorization: str = Header(...)) -> CurrentUser:
    """Extrai e valida a identidade do usuário pelo token Bearer.

    Args:
        authorization: Header Authorization com token Bearer.

    Returns:
        CurrentUser com uid, role, programa_id e email.

    Raises:
        HTTPException(401): Token inválido ou expirado.
        HTTPException(403): Custom claims ausentes (conta não ativada).
    """
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token Bearer ausente",
        )

    token = authorization.removeprefix("Bearer ").strip()

    try:
        init_firebase()
        decoded = auth.verify_id_token(token)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token inválido: {exc}",
        ) from exc

    role = decoded.get("role")
    programa_id = decoded.get("programa_id")

    if not role or not programa_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Conta não ativada: custom claims ausentes",
        )

    return CurrentUser(
        uid=decoded["uid"],
        role=role,
        programa_id=programa_id,
        email=decoded.get("email", ""),
    )
