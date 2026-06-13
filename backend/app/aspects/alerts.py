"""
Aspecto A05 — Geração de Alertas e Notificações (After advice).

Join Point: POST /activities (notifica orientador), PATCH /activities/{id}/validate (notifica aluno).
Advice: After — dispara notificações baseadas no resultado da operação.
Weaving: decorador @trigger_alerts aplicado explicitamente.
"""

from __future__ import annotations

import asyncio
import functools
from collections.abc import Callable
from typing import Any

from backend.app.aspects.aspect_config import ALERTS_ENABLED


def trigger_alerts(func: Callable) -> Callable:
    """Aspecto A05 — Geração de Alertas.

    Join Point: endpoints de submissão e validação de atividades.
    Advice: After — persiste Notification no Firestore após operação bem-sucedida.
    Weaving: decorador Python explícito.

    Args:
        func: Função de endpoint a ser monitorada.

    Returns:
        Wrapper que dispara notificações após a execução.
    """
    @functools.wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        resultado = await func(*args, **kwargs)

        if not ALERTS_ENABLED:
            return resultado

        user = kwargs.get("current_user")
        asyncio.create_task(_dispatch_alert(func.__name__, resultado, user, kwargs))

        return resultado

    return wrapper


async def _dispatch_alert(
    operacao: str,
    resultado: Any,
    user: Any,
    kwargs: dict[str, Any],
) -> None:
    """Determina o tipo de alerta e persiste a notificação."""
    try:
        if operacao in ("submit_activity", "create_activity"):
            await _notify_advisor_new_activity(resultado, user)
        elif operacao in ("validate_activity",):
            await _notify_student_validation(resultado, kwargs.get("activity_id", ""))
    except Exception:
        pass


async def _notify_advisor_new_activity(resultado: Any, user: Any) -> None:
    """Notifica o orientador quando um aluno submete uma atividade."""
    try:
        from backend.app.core.firebase import get_firestore_client
        from google.cloud import firestore as fs

        if not user:
            return

        student_id = getattr(user, "uid", None)
        if not student_id:
            return

        client = get_firestore_client()

        def _read_student() -> dict[str, Any]:
            snap = client.collection("students").document(student_id).get()
            return snap.to_dict() or {} if snap.exists else {}

        student = await asyncio.to_thread(_read_student)
        orientador_id = student.get("orientador_id")
        if not orientador_id:
            return

        activity_id = getattr(resultado, "id", "") if hasattr(resultado, "id") else resultado.get("id", "") if isinstance(resultado, dict) else ""
        nome_aluno = student.get("nome", "Aluno")

        notif = {
            "tipo":            "atividade_submetida",
            "titulo":          "Nova atividade para validação",
            "mensagem":        f"{nome_aluno} submeteu uma atividade para validação.",
            "destinatario_id": orientador_id,
            "entidade_tipo":   "activity",
            "entidade_id":     activity_id,
            "lida":            False,
            "timestamp":       fs.SERVER_TIMESTAMP,
            "programa_id":     student.get("programa_id", ""),
        }

        await asyncio.to_thread(
            lambda: client.collection("notifications").document().set(notif)
        )
    except Exception:
        pass


async def _notify_student_validation(resultado: Any, activity_id: str) -> None:
    """Notifica o aluno sobre o resultado da validação de sua atividade."""
    try:
        from backend.app.core.firebase import get_firestore_client
        from google.cloud import firestore as fs

        client = get_firestore_client()

        # Busca a atividade para encontrar o student_id
        def _find_activity() -> dict[str, Any] | None:
            students = list(client.collection("students").stream())
            for s in students:
                snap = (
                    client.collection("students")
                    .document(s.id)
                    .collection("activities")
                    .document(activity_id)
                    .get()
                )
                if snap.exists:
                    return {"student_id": s.id, **(snap.to_dict() or {})}
            return None

        activity = await asyncio.to_thread(_find_activity)
        if not activity:
            return

        student_id = activity.get("student_id", "")
        novo_status = activity.get("status", "")
        status_label = "aprovada" if novo_status == "aprovado" else "rejeitada"

        notif = {
            "tipo":            "atividade_validada",
            "titulo":          f"Atividade {status_label}",
            "mensagem":        f"Sua atividade foi {status_label}.",
            "destinatario_id": student_id,
            "entidade_tipo":   "activity",
            "entidade_id":     activity_id,
            "lida":            False,
            "timestamp":       fs.SERVER_TIMESTAMP,
            "programa_id":     activity.get("programa_id", ""),
        }

        await asyncio.to_thread(
            lambda: client.collection("notifications").document().set(notif)
        )
    except Exception:
        pass
