"""
Aspecto A02 — Auditoria das Operações (Around advice).

Join Point: qualquer função de service decorada com @audit_operation.
Advice: Around — captura entrada antes + resultado/erro depois; persiste AuditLog.
Weaving: decorador Python + inspect aplicado explicitamente.
"""

from __future__ import annotations

import asyncio
import functools
import inspect
import time
from collections.abc import Callable
from typing import Any

from backend.app.aspects.aspect_config import AUDIT_ENABLED


def _serialize(value: Any) -> Any:
    """Converte valores não-serializáveis para string."""
    try:
        import json
        json.dumps(value)
        return value
    except (TypeError, ValueError):
        return str(value)


def audit_operation(func: Callable) -> Callable:
    """Aspecto A02 — Auditoria das Operações.

    Join Point: funções de service decoradas com @audit_operation.
    Advice: Around — registra quem, o quê, quando e o resultado.
    Weaving: decorador Python explícito.

    Args:
        func: Função a ser auditada.

    Returns:
        Wrapper que persiste AuditLog antes e depois da execução.
    """
    @functools.wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        if not AUDIT_ENABLED:
            return await func(*args, **kwargs)

        # Captura metadados via inspect
        sig = inspect.signature(func)
        try:
            bound = sig.bind(*args, **kwargs)
            bound.apply_defaults()
            arguments = {
                k: _serialize(v)
                for k, v in bound.arguments.items()
                if k not in ("current_user", "self")
            }
        except TypeError:
            arguments = {}

        user = kwargs.get("current_user") or next(
            (v for k, v in kwargs.items() if hasattr(v, "role")), None
        )
        usuario_id = getattr(user, "uid", "sistema") if user else "sistema"
        role = getattr(user, "role", "sistema") if user else "sistema"
        modulo = inspect.getmodule(func)
        modulo_nome = modulo.__name__ if modulo else "desconhecido"

        inicio = time.monotonic()
        resultado_status = "sucesso"
        erro_mensagem = None
        resultado = None

        try:
            resultado = await func(*args, **kwargs)
            return resultado
        except Exception as exc:
            resultado_status = "erro"
            erro_mensagem = str(exc)
            raise
        finally:
            duracao_ms = int((time.monotonic() - inicio) * 1000)

            log = {
                "usuario_id":       usuario_id,
                "role":             role,
                "operacao":         func.__name__,
                "modulo":           modulo_nome,
                "recurso":          arguments.get("activity_id") or arguments.get("student_id") or "",
                "valor_entrada":    arguments,
                "resultado_status": resultado_status,
                "erro_mensagem":    erro_mensagem,
                "duracao_ms":       duracao_ms,
            }

            # Persiste de forma assíncrona sem bloquear o retorno
            asyncio.create_task(_persist_log(log))

    return wrapper


async def _persist_log(log: dict[str, Any]) -> None:
    """Persiste o AuditLog no Firestore de forma assíncrona."""
    try:
        from backend.app.core.firebase import get_firestore_client
        from google.cloud import firestore as fs

        client = get_firestore_client()
        log["timestamp"] = fs.SERVER_TIMESTAMP
        await asyncio.to_thread(lambda: client.collection("audit_logs").document().set(log))
    except Exception:
        pass  # Falha de auditoria nunca deve quebrar a operação principal
