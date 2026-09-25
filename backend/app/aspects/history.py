"""
Aspecto A03 — Histórico de Alterações (Before+After advice).

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
- A entidade e o repositório a versionar são resolvidos pelo nome do parâmetro de id
  presente na assinatura da função decorada (student_id → StudentRepository/"student",
  type_id → ActivityTypeRepository/"activity_type") via _resolve(). A edição do próprio
  perfil (ProfileUpdateRequest no body) versiona users/{uid} via FirebaseRepository("users").
- Weaving via HistoryMeta: envolve automaticamente todos os métodos update_* de subclasses
  de EntityService. Alternativa: @track_history aplicado explicitamente.
"""

from __future__ import annotations

import functools
import inspect
from datetime import datetime, timezone
from typing import Any

from backend.app.aspects import aspect_config
from backend.app.core.auth import CurrentUser
from backend.app.models.user import ProfileUpdateRequest
from backend.app.repositories.activity_type_repository import ActivityTypeRepository
from backend.app.repositories.firebase_repository import FirebaseRepository
from backend.app.repositories.student_repository import StudentRepository
from backend.app.repositories.transfer_repository import TransferRepository

def _resolve(bound_arguments: dict[str, Any]) -> tuple[Any, str, str] | None:
    """Resolve (repositório, entidade_tipo, entidade_id) a partir dos argumentos nomeados.

    Referencia StudentRepository/ActivityTypeRepository pelo nome global do módulo (não
    em um dict pré-construído) para que os testes possam substituí-las via
    monkeypatch.setattr(history_module, "StudentRepository", ...) a cada execução.
    """
    student_id = bound_arguments.get("student_id")
    body = bound_arguments.get("body")
    if student_id is None and body is not None:
        student_id = getattr(body, "student_id", None)
    if isinstance(student_id, str):
        return StudentRepository(), "student", student_id

    type_id = bound_arguments.get("type_id")
    if isinstance(type_id, str):
        return ActivityTypeRepository(), "activity_type", type_id

    if isinstance(body, ProfileUpdateRequest):
        user = next(
            (value for value in bound_arguments.values() if isinstance(value, CurrentUser)),
            None,
        )
        if user is not None:
            return FirebaseRepository("users"), "user", user.uid

    return None


async def _resolve_async(bound_arguments: dict[str, Any]) -> tuple[Any, str, str] | None:
    resolved = _resolve(bound_arguments)
    if resolved is not None:
        return resolved

    transfer_id = bound_arguments.get("transfer_id")
    if isinstance(transfer_id, str):
        request = await TransferRepository().get(transfer_id)
        student_id = request.get("student_id") if request else None
        if isinstance(student_id, str):
            return StudentRepository(), "student", student_id

    return None


def track_history(func):
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        if not aspect_config.HISTORY_ENABLED:
            return await func(*args, **kwargs)

        bound = inspect.signature(func).bind_partial(*args, **kwargs)

        resolved = await _resolve_async(bound.arguments)
        if resolved is None:
            return await func(*args, **kwargs)
        repo, entidade_tipo, entity_id = resolved

        payload = bound.arguments.get("data") or bound.arguments.get("body")
        user = next(
            (
                value
                for value in bound.arguments.values()
                if isinstance(value, CurrentUser)
            ),
            None,
        )

        previous = await repo.get(entity_id)

        result = await func(*args, **kwargs)

        if previous is not None:
            current = await repo.get(entity_id)

            snapshot = {
                "entidade_tipo": entidade_tipo,
                "entidade_id": entity_id,
                "valor_anterior": previous,
                "valor_novo": current,
                "usuario_id": user.uid if user else None,
                "role": user.role if user else None,
                "timestamp": datetime.now(timezone.utc),
            }

            observacao = getattr(payload, "observacao", None)
            if observacao is not None:
                snapshot["observacao"] = observacao

            await repo.save_history_snapshot(entity_id, snapshot)

        return result

    return wrapper
