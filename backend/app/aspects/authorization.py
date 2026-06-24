"""
Aspecto A01 — Autorização por Papel (Before advice).

Responsabilidades:
- Implementar o decorador @requires_role(*roles) usando mecanismos nativos do Python
  (decorador de função, sem bibliotecas externas de AOP).
- Antes de executar a função decorada:
    1. Verifica flag AUTHORIZATION_ENABLED em aspect_config; se False, passa direto.
    2. Extrai CurrentUser do contexto FastAPI (injetado pela dependência get_current_user).
    3. Verifica se user.role está em *roles; se não, lança HTTPException(403).
    4. Para join points com restrição de propriedade (aluno vê próprio, orientador vê
       orientandos): verifica relação no Firestore antes de permitir acesso.
- Join points cobertos: todos os endpoints de mutação e leitura sensível listados na
  spec 02_aspectos_aop.json > aspecto A01.
- Paradigma AOP aplicado: decorador Python como mecanismo de weaving explícito.
"""

from __future__ import annotations

import functools
import inspect
from collections.abc import Awaitable, Callable
from typing import Any, TypeVar

from fastapi import HTTPException, status

from backend.app.aspects import aspect_config
from backend.app.core.auth import CurrentUser

_F = TypeVar("_F", bound=Callable[..., Awaitable[Any]])


def _encontrar_current_user(args: tuple[Any, ...], kwargs: dict[str, Any]) -> CurrentUser | None:
    """Localiza o CurrentUser injetado pelo FastAPI entre os argumentos do endpoint."""
    for value in (*kwargs.values(), *args):
        if isinstance(value, CurrentUser):
            return value
    return None


def requires_role(*roles: str) -> Callable[[_F], _F]:
    """Aspecto A01 — Autorização por Papel.

    Join Point: qualquer endpoint FastAPI decorado com @requires_role, onde o
        CurrentUser é injetado via Depends(get_current_user).
    Advice: Before — verifica o papel do usuário antes de executar a função
        original; bloqueia com HTTPException(403) se o papel não estiver entre
        os permitidos.
    Weaving: decorador Python aplicado manualmente sobre funções de endpoint.

    Args:
        *roles: Papéis autorizados a executar o join point (ex: 'coordenacao').

    Returns:
        Decorador que envolve a função de endpoint com a checagem de papel.
    """

    def decorator(func: _F) -> _F:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            if not aspect_config.AUTHORIZATION_ENABLED:
                return await func(*args, **kwargs)

            user = _encontrar_current_user(args, kwargs)
            if user is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Usuário autenticado ausente no contexto da requisição",
                )

            if user.role not in roles:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Papel insuficiente para executar esta operação",
                )

            return await func(*args, **kwargs)

        return wrapper  # type: ignore[return-value]

    return decorator


def requires_ownership(uid_resolver: Callable[[dict[str, Any]], Any]) -> Callable[[_F], _F]:
    """Aspecto A01 — Autorização por Propriedade.

    Join Point: endpoints onde o acesso deve ser restrito ao dono do recurso
        (ex: orientador só emite parecer em atividades dos próprios orientandos).
    Advice: Before — resolve o uid do dono do recurso via `uid_resolver` e
        compara com current_user.uid; bloqueia com HTTPException(403) se divergir.
    Weaving: decorador Python aplicado manualmente, composto com @requires_role.

    Args:
        uid_resolver: callable que recebe os kwargs do endpoint e retorna o uid
            do proprietário do recurso (pode ser uma coroutine).

    Returns:
        Decorador que envolve a função de endpoint com a checagem de propriedade.
    """

    def decorator(func: _F) -> _F:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            if not aspect_config.AUTHORIZATION_ENABLED:
                return await func(*args, **kwargs)

            user = _encontrar_current_user(args, kwargs)
            if user is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Usuário autenticado ausente no contexto da requisição",
                )

            # Resolve o uid do dono — suporta resolver síncrono e assíncrono
            owner_uid = uid_resolver(kwargs)
            if inspect.isawaitable(owner_uid):
                owner_uid = await owner_uid

            if owner_uid is None or user.uid != owner_uid:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Acesso negado: recurso pertence a outro usuário",
                )

            return await func(*args, **kwargs)

        return wrapper  # type: ignore[return-value]

    return decorator