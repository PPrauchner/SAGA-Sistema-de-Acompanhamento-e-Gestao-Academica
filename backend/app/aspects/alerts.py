"""
Aspecto A05 — Geração de Alertas e Notificações (After advice).

Responsabilidades:
- Implementar o decorador @trigger_alerts(build) usando mecanismos nativos do Python, sem
  bibliotecas externas de AOP.
- After: executa a função original; se ALERTS_ENABLED, chama o `build` (síncrono ou
  assíncrono) com (resultado, args, kwargs) para obter a(s) notificação(ões) a emitir;
  normaliza cada documento (default lida=False e timestamp=agora) e persiste em
  notifications/{auto_id}. Se a função original levantar exceção, nenhum alerta é disparado.
- O `build` é fornecido por quem aplica o aspecto e encapsula a lógica específica do join
  point (destinatário via lookup no Firestore, tipo, título e mensagem). Assim a lógica de
  negócio permanece livre do sistema de alertas, e a fiação a cada endpoint disparador
  (tasks/updates, activities/validate, extensions/approve, prazo crítico) ocorre nas issues
  desses domínios.
- Frontend assina onSnapshot em notifications/ filtrado por destinatario_id para receber
  alertas em tempo real.

Join Point: funções de endpoint/service decoradas com @trigger_alerts(build).
Advice: After — após a execução bem-sucedida da função original, persiste notificação(ões).
Weaving: decorador Python aplicado explicitamente, após @requires_role e @audit_operation
    na ordem canônica de decoradores do projeto.
"""

from __future__ import annotations

import functools
import inspect
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any

from backend.app.aspects import aspect_config
from backend.app.repositories.firebase_repository import FirebaseRepository

NotificationSpec = dict[str, Any]
AlertBuilder = Callable[..., Any]


def _normalize(spec: NotificationSpec) -> NotificationSpec:
    """Aplica os defaults transversais da notificação (lida e timestamp)."""
    doc = dict(spec)
    doc.setdefault("lida", False)
    doc.setdefault("timestamp", datetime.now(timezone.utc))
    return doc


def trigger_alerts(build: AlertBuilder):
    """Aspecto A05 — Geração de Alertas e Notificações.

    Args:
        build: Função (síncrona ou assíncrona) que recebe (resultado, args, kwargs)
            da operação e devolve a notificação a emitir — um dict, uma lista de dicts
            ou None (nenhuma notificação).

    Returns:
        Decorador que envolve a função com o advice After de geração de alertas.
    """

    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            result = await func(*args, **kwargs)

            if not aspect_config.ALERTS_ENABLED:
                return result

            specs = build(result, args, kwargs)
            if inspect.isawaitable(specs):
                specs = await specs

            if not specs:
                return result

            if isinstance(specs, dict):
                specs = [specs]

            repo = FirebaseRepository("notifications")
            for spec in specs:
                await repo.create(_normalize(spec))

            return result

        return wrapper

    return decorator

