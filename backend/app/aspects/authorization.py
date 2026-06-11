"""
Aspecto A01 — Autorização por Papel (Before advice).

Responsabilidades:
- Implementar o decorador @requires_role(*roles) usando mecanismos nativos do Python.
- Verificar o papel do usuário injetado pelo FastAPI.
"""

from functools import wraps
from fastapi import HTTPException
from backend.app.aspects.aspect_config import AUTHORIZATION_ENABLED


def requires_role(*roles: str):
    """Aspecto A01 — Autorização por Papel.
    
    Join Point: qualquer endpoint FastAPI decorado com @requires_role.
    Advice: Before — verifica papel antes de executar a função original.
    Weaving: decorador Python aplicado manualmente sobre funções de negócio.
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            if not AUTHORIZATION_ENABLED:
                return await func(*args, **kwargs)
            
            # O usuário deve estar nos kwargs (injetado pelo Depends(get_current_user))
            user = kwargs.get('user')
            if not user or user.role not in roles:
                raise HTTPException(status_code=403, detail="Acesso negado: papel insuficiente")
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator
