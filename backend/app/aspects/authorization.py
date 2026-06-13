"""
Aspecto A01 — Autorização por Papel (Before advice).

Join Point: qualquer endpoint FastAPI decorado com @requires_role.
Advice: Before — verifica papel antes de executar a função original.
Weaving: decorador Python aplicado manualmente sobre funções de endpoint/service.
"""

from __future__ import annotations

import functools
import inspect
from collections.abc import Callable
from typing import Any

from fastapi import HTTPException, status

from backend.app.aspects.aspect_config import AUTHORIZATION_ENABLED


def requires_role(*roles: str) -> Callable:
    """Aspecto A01 — Autorização por Papel.

    Join Point: qualquer endpoint FastAPI decorado com @requires_role.
    Advice: Before — verifica papel antes de executar a função original.
    Weaving: decorador Python aplicado manualmente.

    Args:
        *roles: Papéis permitidos (ex: 'coordenacao', 'aluno', 'orientador').

    Returns:
        Decorador que protege a função decorada.
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            if not AUTHORIZATION_ENABLED:
                return await func(*args, **kwargs)

            # Extrai CurrentUser dos kwargs (injetado por Depends(get_current_user))
            user = kwargs.get("current_user")
            if user is None:
                # Tenta extrair por posição via inspect
                sig = inspect.signature(func)
                bound = sig.bind(*args, **kwargs)
                bound.apply_defaults()
                user = bound.arguments.get("current_user")

            if user is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Autenticação necessária",
                )

            if user.role not in roles:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Papel insuficiente. Requerido: {list(roles)}. Atual: {user.role}",
                )

            return await func(*args, **kwargs)

        return wrapper
    return decorator
