"""Aspecto A04: validação de prazos."""

from __future__ import annotations

from datetime import date, datetime
from functools import wraps
from typing import Any, Awaitable, Callable, TypeVar

from backend.app.aspects import aspect_config

F = TypeVar("F", bound=Callable[..., Awaitable[Any]])


def _deadline_alert(task: dict[str, Any]) -> bool:
    prazo = task.get("prazo")
    return isinstance(prazo, datetime) and (prazo.date() - date.today()).days <= 7


def _is_overdue(task: dict[str, Any]) -> bool:
    prazo = task.get("prazo")
    return isinstance(prazo, datetime) and prazo.date() < date.today()


async def _apply_deadline_advice(
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
    result: Any,
) -> None:
    self = args[0] if args else None
    task_id = args[1] if len(args) > 1 else kwargs.get("task_id")
    if self is None or task_id is None or not hasattr(self, "_repo"):
        return

    plan, _, task = await self._repo.get_task_context(task_id)
    alerta_prazo = _deadline_alert(task)
    if _is_overdue(task) and task.get("status") != "concluida":
        await self._repo.update_task(task_id, {"status": "atrasada"})
        await self._repo.save_fact(
            plan["student_id"],
            f"prazo_estourado_task({task_id}, {plan['student_id']})",
        )

    if hasattr(result, "alerta_prazo"):
        result.alerta_prazo = alerta_prazo


def check_deadlines(func: F) -> F:
    """Before advice para operações que dependem de prazo de task.

    O join point usado pela issue #44 é `WorkPlanService.add_progress_update`.
    Antes de persistir o progresso, o aspecto verifica o prazo da task; se ele
    já venceu, marca a task como atrasada e registra o fato
    `prazo_estourado_task(task_id, student_id)`.
    """

    @wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        result = await func(*args, **kwargs)
        if aspect_config.DEADLINE_VALIDATION_ENABLED:
            await _apply_deadline_advice(args, kwargs, result)
        return result

    return wrapper  # type: ignore[return-value]
