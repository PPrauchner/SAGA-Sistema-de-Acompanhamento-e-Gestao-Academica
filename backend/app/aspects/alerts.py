"""Aspecto A05: geração de alertas e notificações."""

from __future__ import annotations

from datetime import datetime, timezone
from functools import wraps
from typing import Any, Awaitable, Callable, TypeVar

from backend.app.aspects.aspect_config import ALERTS_ENABLED

F = TypeVar("F", bound=Callable[..., Awaitable[Any]])


def trigger_alerts(func: F) -> F:
    """After advice para persistir notificações no padrão `notifications/`.

    No join point de progresso de task, o destinatário é o orientador do plano.
    O documento segue o contrato usado pelo frontend:
    `{tipo, titulo, mensagem, destinatario_id, entidade_id, lida, timestamp}`.
    """

    @wraps(func)
    async def wrapper(self: Any, task_id: str, *args: Any, **kwargs: Any) -> Any:
        result = await func(self, task_id, *args, **kwargs)
        if not ALERTS_ENABLED:
            return result

        plan, _, task = await self._repo.get_task_context(task_id)
        actor = kwargs.get("actor")
        if actor is None and len(args) >= 2:
            actor = args[1]
        actor_name = getattr(actor, "nome", "Aluno")

        notification = {
            "tipo": "progresso_task",
            "titulo": "Progresso registrado",
            "mensagem": f"{actor_name} registrou progresso em {task['titulo']}",
            "destinatario_id": plan.get("orientador_id", "orientador"),
            "entidade_id": task_id,
            "lida": False,
            "timestamp": datetime.now(timezone.utc),
        }
        await self._repo.create_notification(notification)
        if hasattr(result, "notificacao_enviada_ao_orientador"):
            result.notificacao_enviada_ao_orientador = True
        return result

    return wrapper  # type: ignore[return-value]
