"""
FastAPI dependency for authentication and identity extraction via Firebase Auth.

Responsabilidades:
- Define the CurrentUser Pydantic model.
- Implement the get_current_user dependency.
"""

from typing import Annotated
from pydantic import BaseModel
from fastapi import Depends, Header, HTTPException, status
from backend.app.core.firebase import get_auth_client


class CurrentUser(BaseModel):
    """Model representing the currently authenticated user."""
    uid: str
    role: str
    programa_id: str
    email: str


async def get_current_user(
    authorization: Annotated[str | None, Header()] = None
) -> CurrentUser:
    """Dependency to extract and verify the current user from the Authorization header.

    In a real scenario, this would verify the Firebase ID token.
    For now, it's a stub that should be properly implemented in Issue #40.
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de autenticação ausente",
        )
    
    # Minimal stub logic: for testing purposes, we might want to bypass or mock this.
    # In production, this would use firebase_admin.auth.verify_id_token(token)
    
    # For Issue #47 to work in a local dev environment without a real token:
    # We'll assume the token is just the UID for now if it's not a real JWT.
    # THIS IS A STUB.
    
    try:
        # In a real implementation, we'd decode the token here.
        # token = authorization.split("Bearer ")[1]
        # decoded_token = auth.verify_id_token(token)
        # return CurrentUser(...)
        
        # Placeholder for development/testing
        return CurrentUser(
            uid="stub_uid",
            role="coordenacao",
            programa_id="prog_default",
            email="admin@saga.edu"
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token inválido: {str(exc)}",
        )
