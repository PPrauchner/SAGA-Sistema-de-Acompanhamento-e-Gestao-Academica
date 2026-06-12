"""
Aspecto A03 — Histórico de Alterações das Entidades (Before + After advice).

Responsabilidades:
- Implementar HistoryMeta (metaclasse) ou decorador @track_history para versionar entidades
  que mudam ao longo do tempo, sem bibliotecas externas de AOP.
- Before: lê estado atual da entidade no Firestore via repositório (valor_anterior).
- Executa o método original de update (persiste o novo estado).
- After: monta HistorySnapshot com {entidade_tipo, entidade_id, valor_anterior, valor_novo,
  usuario_id, role, timestamp} e persiste em sub-coleção history/ da entidade.
- Entidades cobertas: PlanoTrabalho (update_plan), TipoAtividadeCreditavel (update_type,
  toggle_active), SituacaoRegistrada do aluno (update_situacao_registrada), qualificacao e
  proficiencia do aluno.
- Weaving via HistoryMeta: envolve automaticamente todos os métodos update_* de subclasses
  de EntityService. Alternativa: @track_history aplicado explicitamente.
"""

from __future__ import annotations

import functools
import inspect
from datetime import datetime, timezone

from backend.app.aspects import aspect_config
from backend.app.core.auth import CurrentUser
from backend.app.repositories.student_repository import StudentRepository


def track_history(func):
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        if not aspect_config.HISTORY_ENABLED:
            return await func(*args, **kwargs)

        bound = inspect.signature(func).bind_partial(*args, **kwargs)
        student_id = bound.arguments.get("student_id")
        user = next(
            (
                value
                for value in bound.arguments.values()
                if isinstance(value, CurrentUser)
            ),
            None,
        )

        repo = StudentRepository()

        previous = None

        if student_id:
            previous = await repo.get(student_id)

        result = await func(*args, **kwargs)

        if student_id and previous:
            current = await repo.get(student_id)

            await repo.save_history_snapshot(
                student_id,
                {
                    "entidade_tipo": "student",
                    "entidade_id": student_id,
                    "valor_anterior": previous,
                    "valor_novo": current,
                    "usuario_id": user.uid if user else None,
                    "role": user.role if user else None,
                    "timestamp": datetime.now(timezone.utc),
                },
            )

        return result

    return wrapper
