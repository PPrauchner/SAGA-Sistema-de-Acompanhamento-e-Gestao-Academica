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
"""
A01 — Aspecto de Autorização

Advice: Before
Mecanismo: Decorador @requires_role e @requires_ownership

Join Points:
- Qualquer operação sensível que exija papel específico
- Operações que exigem que o usuário seja o orientador do aluno (por propriedade)

Conceitos AOP:
- Join Point: chamada da função decorada
- Advice (Before): verifica permissão antes de executar a função
- Weaving: aplicado via decorador em tempo de definição
"""

import functools
import logging
from typing import Callable

from fastapi import HTTPException, status

from backend.app.aspects.aspect_config import AUTHORIZATION_ENABLED

logger = logging.getLogger(__name__)


def requires_role(*allowed_roles: str) -> Callable:
    """
    Decorador Before que verifica se o usuário possui um dos papéis permitidos.

    Join Point: entrada da função de serviço ou endpoint.
    Advice: bloqueia execução se papel não autorizado.
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            if not AUTHORIZATION_ENABLED:
                return await func(*args, **kwargs)

            current_user: dict = kwargs.get("current_user") or (
                args[0] if args else None
            )
            # Busca current_user em kwargs independente da posição
            for v in list(kwargs.values()) + list(args):
                if isinstance(v, dict) and "role" in v:
                    current_user = v
                    break

            if current_user is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Usuário não autenticado.",
                )

            if current_user["role"] not in allowed_roles:
                logger.warning(
                    "[A01] Acesso negado: uid=%s role=%s tentou acessar %s (permitido: %s)",
                    current_user.get("uid"),
                    current_user.get("role"),
                    func.__name__,
                    allowed_roles,
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Papel '{current_user['role']}' não autorizado para esta operação.",
                )

            logger.debug(
                "[A01] Acesso permitido: uid=%s role=%s -> %s",
                current_user.get("uid"),
                current_user.get("role"),
                func.__name__,
            )
            return await func(*args, **kwargs)

        return wrapper
    return decorator


def requires_ownership(get_owner_uid_fn: Callable) -> Callable:
    """
    Decorador Before que verifica se o usuário logado é o orientador do aluno
    dono do recurso (verificação por propriedade).

    get_owner_uid_fn: função async(kwargs) -> str  que retorna o uid do orientador
                      responsável pelo recurso sendo acessado.

    Join Point: entrada da função de serviço.
    Advice: bloqueia execução se usuário não for o dono/orientador.
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            if not AUTHORIZATION_ENABLED:
                return await func(*args, **kwargs)

            current_user: dict | None = None
            for v in list(kwargs.values()) + list(args):
                if isinstance(v, dict) and "role" in v:
                    current_user = v
                    break

            if current_user is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Usuário não autenticado.",
                )

            # Coordenação passa direto (tem acesso total)
            if current_user["role"] == "coordenacao":
                return await func(*args, **kwargs)

            owner_uid = await get_owner_uid_fn(kwargs)

            if owner_uid is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Recurso não encontrado.",
                )

            if current_user["uid"] != owner_uid:
                logger.warning(
                    "[A01] Violação de propriedade: uid=%s tentou acessar recurso de %s em %s",
                    current_user.get("uid"),
                    owner_uid,
                    func.__name__,
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Você não é o orientador deste aluno.",
                )

            logger.debug(
                "[A01] Propriedade verificada: uid=%s -> %s",
                current_user.get("uid"),
                func.__name__,
            )
            return await func(*args, **kwargs)

        return wrapper
    return decorator