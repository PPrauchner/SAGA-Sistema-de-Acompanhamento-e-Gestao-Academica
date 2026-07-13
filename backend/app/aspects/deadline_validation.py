"""Aspecto A04: validação de prazos.

Join Point:
- After: `WorkPlanService.add_progress_update` (via `POST /tasks/{id}/updates`) —
  depois de registrar o progresso, verifica o prazo da task; se venceu, marca a
  task como atrasada e registra o fato `prazo_estourado_task` (#44).
- Before: `create_extension` (via `POST /api/v1/extensions`) — antes de criar a
  solicitação, bloqueia quando o aluno já atingiu `programs.max_prorrogacoes` ou
  quando o prazo final expirou há mais dias do que a janela permitida (#240).

Advice: Before + After.
Weaving: decorador `@check_deadlines` aplicado sobre endpoints/métodos que operam
    sobre dados temporalmente sensíveis. Ativável por `aspect_config`.
"""

from __future__ import annotations

from datetime import date, datetime
from functools import wraps
from typing import Any, Awaitable, Callable, TypeVar

from fastapi import HTTPException, status

from backend.app.aspects import aspect_config
from backend.app.repositories.program_repository import ProgramRepository

F = TypeVar("F", bound=Callable[..., Awaitable[Any]])

# Fallback quando o programa não define o limite (default do modelo, ver
# docs/data-model.md → programs.max_prorrogacoes).
DEFAULT_MAX_PRORROGACOES = 1


def _to_date(value: Any) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return None


def _deadline_alert(task: dict[str, Any]) -> bool:
    prazo = task.get("prazo")
    return isinstance(prazo, datetime) and (prazo.date() - date.today()).days <= 7


def _is_overdue(task: dict[str, Any]) -> bool:
    prazo = task.get("prazo")
    return isinstance(prazo, datetime) and prazo.date() < date.today()


def _find_with_attrs(args: tuple[Any, ...], kwargs: dict[str, Any], *attrs: str) -> Any:
    """Localiza o primeiro argumento que expõe todos os atributos indicados."""
    for value in (*kwargs.values(), *args):
        if all(hasattr(value, attr) for attr in attrs):
            return value
    return None


async def _max_prorrogacoes(programa_id: str | None) -> int:
    config = await ProgramRepository().get_config(programa_id) if programa_id else None
    return (config or {}).get("max_prorrogacoes", DEFAULT_MAX_PRORROGACOES)


async def _ensure_can_request_extension(service: Any, student: dict[str, Any]) -> None:
    """Bloqueia a solicitação fora das condições da RL/spec 08 (Before).

    Args:
        service: `ExtensionService` da request — dá acesso ao repositório de
            prorrogações (`_repo`) para contar as já aprovadas.
        student: Aluno-alvo já resolvido pelo service.

    Raises:
        HTTPException: 409 se o aluno já atingiu `programs.max_prorrogacoes`;
            422 se o prazo final expirou além da janela de solicitação.
    """
    aprovadas = await service._repo.count_approved_for_student(student["id"])
    if aprovadas >= await _max_prorrogacoes(student.get("programa_id")):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Aluno ja atingiu o numero maximo de prorrogacoes",
        )

    prazo_final = _to_date(student.get("prazo_final"))
    if prazo_final is not None:
        dias_expirado = (date.today() - prazo_final).days
        if dias_expirado > aspect_config.DIAS_LIMITE_SOLICITAR_PRORROGACAO:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Prazo final expirado ha mais de "
                f"{aspect_config.DIAS_LIMITE_SOLICITAR_PRORROGACAO} dias; "
                "fora da janela para solicitar prorrogacao",
            )


async def _apply_extension_precheck(args: tuple[Any, ...], kwargs: dict[str, Any]) -> None:
    """Before advice do join point de prorrogação.

    Detecta o join point pela presença de um `ExtensionService` (expõe
    `_resolve_target_student`), do corpo da request e do usuário autenticado.
    Fora desse join point (ex.: task update) é um no-op.
    """
    service = _find_with_attrs(args, kwargs, "_resolve_target_student", "_repo")
    body = _find_with_attrs(args, kwargs, "tipo", "motivo")
    user = _find_with_attrs(args, kwargs, "uid", "role")
    if service is None or body is None or user is None:
        return

    student = await service._resolve_target_student(getattr(body, "student_id", None), user)
    await _ensure_can_request_extension(service, student)


async def _apply_deadline_advice(
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
    result: Any,
) -> None:
    self = next((value for value in (*kwargs.values(), *args) if hasattr(value, "_repo")), None)
    task_id = kwargs.get("task_id") or next((value for value in args if isinstance(value, str)), None)
    if self is None or task_id is None or not hasattr(self, "_repo"):
        return
    if not hasattr(self._repo, "get_task_context"):
        return

    plan, _, task = await self._repo.get_task_context(task_id)
    alerta_prazo = _deadline_alert(task)
    if _is_overdue(task) and task.get("status") != "concluido":
        await self._repo.update_task(task_id, {"status": "atrasado"})
        await self._repo.save_fact(
            plan["student_id"],
            f"prazo_estourado_task({task_id}, {plan['student_id']})",
        )

    if hasattr(result, "alerta_prazo"):
        result.alerta_prazo = alerta_prazo


def check_deadlines(func: F) -> F:
    """Before + After advice para operações temporalmente sensíveis.

    Before (`_apply_extension_precheck`): no join point de prorrogação, valida
    `max_prorrogacoes` e a janela do prazo final antes de criar a solicitação.
    After (`_apply_deadline_advice`): no join point de task (#44), verifica o
    prazo depois de registrar o progresso. Cada join point é detectado pelos
    argumentos; fora dele o advice correspondente é no-op.
    """

    @wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        if aspect_config.DEADLINE_VALIDATION_ENABLED:
            await _apply_extension_precheck(args, kwargs)
        result = await func(*args, **kwargs)
        if aspect_config.DEADLINE_VALIDATION_ENABLED:
            await _apply_deadline_advice(args, kwargs, result)
        return result

    return wrapper  # type: ignore[return-value]
