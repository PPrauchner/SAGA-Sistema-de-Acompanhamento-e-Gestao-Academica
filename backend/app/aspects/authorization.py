import functools
import inspect
import logging
from typing import Callable

from fastapi import HTTPException, status

from backend.app.aspects import aspect_config

logger = logging.getLogger(__name__)


def _extract_current_user(args, kwargs) -> dict | None:
    for v in list(kwargs.values()) + list(args):
        if isinstance(v, dict) and "role" in v:
            return v
        if hasattr(v, "role") and hasattr(v, "uid"):
            return {"uid": v.uid, "email": getattr(v, "email", None), "role": v.role}
    return None


def requires_role(*allowed_roles: str) -> Callable:
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            if not aspect_config.AUTHORIZATION_ENABLED:
                return await func(*args, **kwargs)

            current_user = _extract_current_user(args, kwargs)

            if current_user is None:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                    detail="Usuário não autenticado.")

            if current_user["role"] not in allowed_roles:
                logger.warning("[A01] Acesso negado: uid=%s role=%s tentou acessar %s (permitido: %s)",
                               current_user.get("uid"), current_user.get("role"), func.__name__, allowed_roles)
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                    detail=f"Papel '{current_user['role']}' não autorizado para esta operação.")

            return await func(*args, **kwargs)
        return wrapper
    return decorator


def requires_ownership(get_owner_uid_fn: Callable) -> Callable:
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            if not aspect_config.AUTHORIZATION_ENABLED:
                return await func(*args, **kwargs)

            current_user = _extract_current_user(args, kwargs)

            if current_user is None:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                    detail="Usuário não autenticado.")

            if current_user["role"] == "coordenacao":
                return await func(*args, **kwargs)

            # Suporta funções síncronas e assíncronas
            res = get_owner_uid_fn(kwargs)
            owner_uid = await res if inspect.isawaitable(res) else res

            if owner_uid is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                    detail="Recurso não encontrado.")

            if current_user["uid"] != owner_uid:
                logger.warning("[A01] Violação de propriedade: uid=%s tentou acessar recurso de %s em %s",
                               current_user.get("uid"), owner_uid, func.__name__)
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                    detail="Você não é o orientador deste aluno.")

            return await func(*args, **kwargs)
        return wrapper
    return decorator