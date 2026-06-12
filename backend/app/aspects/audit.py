"""
Aspecto A02 — Auditoria das Operações (Around advice).

Responsabilidades:
- Implementar o decorador @audit_operation usando inspect para captura de metadados em
  tempo de execução, sem bibliotecas externas de AOP.
- Before (captura): usa inspect.signature(func).bind(*args, **kwargs).arguments para
  extrair parâmetros nomeados; registra timestamp_inicio, usuario_id, role, operacao e
  entidade_afetada_id.
- Executa a função original (await func(*args, **kwargs)).
- After (persiste): monta documento AuditLog com {usuario_id, role, operacao, modulo
  (via inspect.getmodule), recurso, valor_entrada, resultado_status, erro_mensagem,
  timestamp, duracao_ms} e persiste em audit_logs/{auto_id} no Firestore.
- Em caso de exceção: registra erro no AuditLog e re-lança a exceção.
- Paradigma AOP: decorador Python + inspect como mecanismo de weaving explícito.
"""
from __future__ import annotations

import functools
from datetime import datetime, timezone
from typing import Any

from backend.app.aspects import aspect_config
from backend.app.core.auth import CurrentUser
from backend.app.repositories.firebase_repository import FirebaseRepository


def _find_user(
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
) -> CurrentUser | None:
    for value in (*kwargs.values(), *args):
        if isinstance(value, CurrentUser):
            return value
    return None


def audit_operation(func):
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        if not aspect_config.AUDIT_ENABLED:
            return await func(*args, **kwargs)

        user = _find_user(args, kwargs)

        repo = FirebaseRepository("audit_logs")

        started_at = datetime.now(timezone.utc)

        try:
            result = await func(*args, **kwargs)

            finished_at = datetime.now(timezone.utc)

            await repo.set(
                str(finished_at.timestamp()),
                {
                    "usuario_id": user.uid if user else None,
                    "role": user.role if user else None,
                    "operacao": func.__name__,
                    "resultado_status": "sucesso",
                    "timestamp": finished_at,
                    "duracao_ms": int(
                        (finished_at - started_at).total_seconds() * 1000
                    ),
                },
            )

            return result

        except Exception as exc:
            finished_at = datetime.now(timezone.utc)

            await repo.set(
                str(finished_at.timestamp()),
                {
                    "usuario_id": user.uid if user else None,
                    "role": user.role if user else None,
                    "operacao": func.__name__,
                    "resultado_status": "erro",
                    "erro_mensagem": str(exc),
                    "timestamp": finished_at,
                    "duracao_ms": int(
                        (finished_at - started_at).total_seconds() * 1000
                    ),
                },
            )

            raise

    return wrapper
