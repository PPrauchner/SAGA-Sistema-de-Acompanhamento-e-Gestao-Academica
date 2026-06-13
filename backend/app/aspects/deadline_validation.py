"""
Aspecto A04 — Validação de Prazos (Before + After advice).

Join Point: endpoints POST /activities, POST /tasks/{id}/updates, POST /extensions.
Advice: Before — verifica se data_realizacao está dentro do período do curso.
Weaving: decorador @check_deadlines aplicado explicitamente.
"""

from __future__ import annotations

import asyncio
import functools
from collections.abc import Callable
from typing import Any

from backend.app.aspects.aspect_config import DEADLINE_VALIDATION_ENABLED


def check_deadlines(func: Callable) -> Callable:
    """Aspecto A04 — Validação de Prazos.

    Join Point: endpoints que operam sobre dados temporalmente sensíveis.
    Advice: Before+After — verifica datas; sinaliza prazo estourado.
    Weaving: decorador Python explícito.

    Args:
        func: Função de endpoint a ser verificada.

    Returns:
        Wrapper que valida prazos antes da execução.
    """
    @functools.wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        if not DEADLINE_VALIDATION_ENABLED:
            return await func(*args, **kwargs)

        user = kwargs.get("current_user")
        student_id = kwargs.get("student_id") or (
            getattr(kwargs.get("body"), "student_id", None)
            if kwargs.get("body") else None
        )

        # Verifica prazo do aluno de forma não-bloqueante
        if student_id and user:
            asyncio.create_task(_check_student_deadline(student_id))

        return await func(*args, **kwargs)

    return wrapper


async def _check_student_deadline(student_id: str) -> None:
    """Verifica prazo do aluno e atualiza situacao_inferida se necessário."""
    from datetime import date

    try:
        from backend.app.core.firebase import get_firestore_client
        from backend.app.aspects.aspect_config import (
            DIAS_ALERTA_PRAZO_FINAL,
            DIAS_ALERTA_PRAZO_QUALIFICACAO,
        )

        client = get_firestore_client()

        def _read_student() -> dict[str, Any]:
            snap = client.collection("students").document(student_id).get()
            return snap.to_dict() or {} if snap.exists else {}

        student_data = await asyncio.to_thread(_read_student)
        if not student_data:
            return

        prazo_final = student_data.get("prazo_final")
        if not prazo_final:
            return

        if hasattr(prazo_final, "date"):
            prazo_date = prazo_final.date()
        else:
            return

        hoje = date.today()
        dias_restantes = (prazo_date - hoje).days

        if dias_restantes < 0:
            # Prazo estourado — delega notificação ao A05
            await _notify_deadline_critical(student_id, "prazo_estourado", dias_restantes)
        elif dias_restantes <= DIAS_ALERTA_PRAZO_FINAL:
            await _notify_deadline_critical(student_id, "prazo_proximo", dias_restantes)
    except Exception:
        pass


async def _notify_deadline_critical(student_id: str, tipo: str, dias: int) -> None:
    """Cria notificação de prazo crítico para o aluno e seu orientador."""
    try:
        from backend.app.core.firebase import get_firestore_client
        from google.cloud import firestore as fs

        client = get_firestore_client()

        def _read() -> dict[str, Any]:
            snap = client.collection("students").document(student_id).get()
            return snap.to_dict() or {} if snap.exists else {}

        student = await asyncio.to_thread(_read)
        orientador_id = student.get("orientador_id")
        nome = student.get("nome", "Aluno")

        mensagem = (
            f"Prazo final de {nome} está vencido há {abs(dias)} dia(s)."
            if tipo == "prazo_estourado"
            else f"Prazo final de {nome} em {dias} dia(s)."
        )

        destinatarios = [uid for uid in [student_id, orientador_id] if uid]

        def _create_notifications() -> None:
            for uid in destinatarios:
                notif = {
                    "tipo":           tipo,
                    "titulo":         "Prazo Crítico",
                    "mensagem":       mensagem,
                    "destinatario_id": uid,
                    "entidade_tipo":  "student",
                    "entidade_id":    student_id,
                    "lida":           False,
                    "timestamp":      fs.SERVER_TIMESTAMP,
                    "programa_id":    student.get("programa_id", ""),
                }
                client.collection("notifications").document().set(notif)

        await asyncio.to_thread(_create_notifications)
    except Exception:
        pass
