"""
Aspecto A03 — Histórico de Alterações das Entidades (Before + After advice).

Join Point: métodos de service decorados com @track_history.
Advice: Before — lê estado anterior; After — persiste HistorySnapshot.
Weaving: decorador @track_history aplicado explicitamente nos join points.
"""

from __future__ import annotations

import asyncio
import functools
from collections.abc import Callable
from typing import Any

from backend.app.aspects.aspect_config import HISTORY_ENABLED


def track_history(collection: str, id_kwarg: str = "type_id") -> Callable:
    """Aspecto A03 — Histórico de Alterações.

    Join Point: métodos update_* e toggle_* de services.
    Advice: Before+After — captura estado anterior e persiste snapshot imutável.
    Weaving: decorador Python aplicado explicitamente.

    Args:
        collection: Coleção Firestore onde a entidade vive (ex: 'activity_types').
        id_kwarg: Nome do kwarg que contém o ID do documento.

    Returns:
        Decorador que versiona a entidade antes e depois da operação.
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            if not HISTORY_ENABLED:
                return await func(*args, **kwargs)

            doc_id = kwargs.get(id_kwarg)
            user = kwargs.get("current_user")
            usuario_id = getattr(user, "uid", "sistema") if user else "sistema"
            role = getattr(user, "role", "sistema") if user else "sistema"

            # Before: captura estado anterior
            valor_anterior: dict[str, Any] = {}
            if doc_id:
                try:
                    from backend.app.core.firebase import get_firestore_client
                    client = get_firestore_client()

                    def _read() -> dict[str, Any]:
                        snap = client.collection(collection).document(doc_id).get()
                        return snap.to_dict() or {} if snap.exists else {}

                    valor_anterior = await asyncio.to_thread(_read)
                except Exception:
                    pass

            # Executa a operação
            resultado = await func(*args, **kwargs)

            # After: persiste snapshot
            if doc_id:
                asyncio.create_task(_persist_snapshot(
                    collection=collection,
                    doc_id=doc_id,
                    valor_anterior=valor_anterior,
                    valor_novo=resultado if isinstance(resultado, dict) else {},
                    usuario_id=usuario_id,
                    role=role,
                ))

            return resultado

        return wrapper
    return decorator


async def _persist_snapshot(
    collection: str,
    doc_id: str,
    valor_anterior: dict[str, Any],
    valor_novo: dict[str, Any],
    usuario_id: str,
    role: str,
) -> None:
    """Persiste o HistorySnapshot na sub-coleção history/ da entidade."""
    try:
        from backend.app.core.firebase import get_firestore_client
        from google.cloud import firestore as fs

        client = get_firestore_client()
        snapshot = {
            "entidade_tipo":   collection,
            "entidade_id":     doc_id,
            "valor_anterior":  valor_anterior,
            "valor_novo":      valor_novo,
            "usuario_id":      usuario_id,
            "role":            role,
            "timestamp":       fs.SERVER_TIMESTAMP,
        }
        history_ref = (
            client.collection(collection)
            .document(doc_id)
            .collection("history")
            .document()
        )
        await asyncio.to_thread(lambda: history_ref.set(snapshot))
    except Exception:
        pass
