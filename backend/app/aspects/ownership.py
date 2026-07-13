"""
Aspecto — Autorização de Propriedade (Ownership Check).

Responsabilidades:
- Implementar o decorador @check_dashboard_ownership para garantir
  que alunos só acessem seus próprios dashboards e orientadores
  só acessem dashboards dos seus orientandos.
- Implementar o decorador @check_work_plan_ownership para o plano de
  trabalho / kanban: a edição depende de ser o orientador do aluno
  (ownership), não do papel; a coordenação é read-only.
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


def _resolve_student_id(kwargs: dict[str, Any]) -> str | None:
    """Resolve o id do documento do aluno a partir dos parâmetros do endpoint.

    `student_id` vem direto. Os ids de plano/etapa/task codificam o aluno no
    primeiro segmento (`student_id~plan~stage~task`, ver WorkPlanRepository);
    como auto-ids do Firestore não contêm `~`, o primeiro segmento é sempre o
    id do documento do aluno.

    Args:
        kwargs: Argumentos nomeados do endpoint.

    Returns:
        O id do documento do aluno, ou None se nenhum parâmetro identificar o recurso.
    """
    student_id = kwargs.get("student_id")
    if student_id:
        return student_id
    for param in ("plan_id", "stage_id", "task_id"):
        value = kwargs.get(param)
        if value:
            return value.split("~", 1)[0]
    return None


async def _is_advisor_of(uid: str, student: dict[str, Any]) -> bool:
    """Indica se o usuário `uid` é orientador ou coorientador do aluno.

    Args:
        uid: uid Firebase do usuário autenticado.
        student: Documento do aluno (com `orientador_id` / `coorientador_id`).

    Returns:
        True se algum `advisors/{id}` do usuário casa com orientador_id ou
        coorientador_id do aluno.
    """
    advisors_repo = FirebaseRepository("advisors")
    advisors = await advisors_repo.query(filters=[("uid", "==", uid)])
    advisor_ids = {advisor["id"] for advisor in advisors}
    if not advisor_ids:
        return False
    return (
        student.get("orientador_id") in advisor_ids
        or student.get("coorientador_id") in advisor_ids
    )


def check_work_plan_ownership(access: str) -> Callable[[_F], _F]:
    """Aspecto A01 — Propriedade do plano de trabalho (ownership).

    Join Point: endpoints FastAPI de plano de trabalho que recebem
        student_id, plan_id, stage_id ou task_id.
    Advice: Before — resolve o aluno do recurso e valida a relação do usuário
        autenticado conforme o nível de acesso:
        - "read":   aluno dono OU orientador/coorientador OU coordenação.
        - "edit":   apenas orientador/coorientador do aluno; coordenação sem
                    vínculo de orientação e aluno recebem 403 (kanban read-only).
        - "status": aluno dono OU orientador/coorientador (mover status da task).
        O direito de editar vem da relação de orientação, não do papel: um
        coordenador que também orienta o aluno edita via ownership.
    Weaving: decorador Python aplicado manualmente abaixo de @requires_role.

    Args:
        access: Nível de acesso exigido — "read", "edit" ou "status".

    Returns:
        Decorador que envolve o endpoint com a checagem de propriedade.
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

            student_id = _resolve_student_id(kwargs)
            if not student_id:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Recurso de plano de trabalho não identificado",
                )

            student = await FirebaseRepository("students").get(student_id)
            if not student:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Aluno não encontrado",
                )

            is_owner_aluno = user.role == "aluno" and student.get("uid") == user.uid
            is_advisor = False
            if user.role in ("orientador", "coordenacao"):
                is_advisor = await _is_advisor_of(user.uid, student)

            if access == "read":
                allowed = is_owner_aluno or is_advisor or user.role == "coordenacao"
            elif access == "edit":
                allowed = is_advisor
            else:  # "status"
                allowed = is_owner_aluno or is_advisor

            if not allowed:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Acesso negado: você não é o orientador deste aluno",
                )

            return await func(*args, **kwargs)

        return wrapper

    return decorator
