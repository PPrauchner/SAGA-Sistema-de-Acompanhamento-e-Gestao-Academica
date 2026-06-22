"""
Aspecto — Autorização de Propriedade (Ownership Check).

Responsabilidades:
- Implementar o decorador @check_dashboard_ownership para garantir
  que alunos só acessem seus próprios dashboards e orientadores
  só acessem dashboards dos seus orientandos.
"""

from __future__ import annotations

import functools
from collections.abc import Awaitable, Callable
from typing import Any, TypeVar

from fastapi import HTTPException, status

from backend.app.aspects import aspect_config
from backend.app.core.auth import CurrentUser
from backend.app.repositories.firebase_repository import FirebaseRepository

_F = TypeVar("_F", bound=Callable[..., Awaitable[Any]])


def _encontrar_current_user(args: tuple[Any, ...], kwargs: dict[str, Any]) -> CurrentUser | None:
    """Localiza o CurrentUser injetado pelo FastAPI entre os argumentos do endpoint."""
    for value in (*kwargs.values(), *args):
        if isinstance(value, CurrentUser):
            return value
    return None


def check_dashboard_ownership() -> Callable[[_F], _F]:
    """Aspecto — Verificação de Propriedade (Ownership).

    Join Point: endpoints FastAPI de dashboard que recebem student_id ou advisor_id
        e exigem verificação de propriedade.
    Advice: Before — verifica se o usuário autenticado é o dono do recurso solicitado.
        - Se for aluno acessando student_id, user.uid deve bater com student.uid.
        - Se for orientador acessando student_id, o student.orientador_id deve bater
          com o id interno do orientador.
        - Se for orientador acessando advisor_id, o user.uid deve bater com o uid
          interno do advisor_id (ou seja, deve ser ele mesmo).
    Weaving: decorador Python aplicado manualmente sobre funções de endpoint.

    Returns:
        Decorador que envolve a função de endpoint com a checagem de ownership.
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

            if user.role == "coordenacao":
                return await func(*args, **kwargs)

            student_id = kwargs.get("student_id")
            if student_id:
                students_repo = FirebaseRepository("students")
                student = await students_repo.get(student_id)
                if not student:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Aluno não encontrado",
                    )
                
                if user.role == "aluno":
                    if student.get("uid") != user.uid:
                        raise HTTPException(
                            status_code=status.HTTP_403_FORBIDDEN,
                            detail="Acesso negado: aluno só pode acessar próprio dashboard",
                        )
                
                elif user.role == "orientador":
                    advisors_repo = FirebaseRepository("advisors")
                    advisors = await advisors_repo.query(filters=[("uid", "==", user.uid)])
                    if not advisors:
                        raise HTTPException(
                            status_code=status.HTTP_403_FORBIDDEN,
                            detail="Acesso negado: orientador não encontrado no sistema",
                        )
                    advisor_id_from_uid = advisors[0]["id"]
                    if student.get("orientador_id") != advisor_id_from_uid:
                        raise HTTPException(
                            status_code=status.HTTP_403_FORBIDDEN,
                            detail="Acesso negado: o aluno não é seu orientando",
                        )

            advisor_id = kwargs.get("advisor_id")
            if advisor_id and user.role == "orientador":
                advisors_repo = FirebaseRepository("advisors")
                advisor = await advisors_repo.get(advisor_id)
                if not advisor:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Orientador não encontrado",
                    )
                if advisor.get("uid") != user.uid:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Acesso negado: orientador só pode acessar próprio dashboard",
                    )

            return await func(*args, **kwargs)

        return wrapper

    return decorator
