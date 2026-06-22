"""
Aspecto A02 — Auditoria das Operações (Around advice).

Responsabilidades:
- Implementar o decorador @audit_operation usando inspect para captura de metadados em
  tempo de execução, sem bibliotecas externas de AOP.
- Before (captura): usa inspect.signature(func).bind_partial(*args, **kwargs).arguments para
  extrair parâmetros nomeados (valor_entrada); registra timestamp_inicio, usuario_id, role,
  programa_id, operacao e modulo (via inspect.getmodule).
- Executa a função original (await func(*args, **kwargs)).
- After (persiste): monta documento AuditLog com {usuario_id, role, programa_id, operacao,
  modulo, recurso, valor_entrada, resultado_status, erro_mensagem, timestamp, duracao_ms}
  e persiste em audit_logs/{auto_id} no Firestore.
- Em caso de exceção: registra erro no AuditLog e re-lança a exceção.
- Paradigma AOP: decorador Python + inspect como mecanismo de weaving explícito.
"""
from __future__ import annotations

import functools
import inspect
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel

from backend.app.aspects import aspect_config
from backend.app.core.auth import CurrentUser
from backend.app.repositories.firebase_repository import FirebaseRepository

_ENTITY_SUFFIXES = ("_service", "_repository")

SENSITIVE_FIELDS: frozenset[str] = frozenset(
    {"password", "senha", "token", "secret", "api_key", "private_key", "refresh_token"}
)

_REDACTED = "***"


def _find_user(
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
) -> CurrentUser | None:
    for value in (*kwargs.values(), *args):
        if isinstance(value, CurrentUser):
            return value
    return None


def _redact_sensitive(data: dict[str, Any]) -> dict[str, Any]:
    """Substitui valores de campos sensíveis por '***' em valor_entrada.

    Percorre o dict recursivamente para cobrir payloads aninhados. A denylist
    centralizada é SENSITIVE_FIELDS; adicionar uma chave lá basta para protegê-la
    em todos os endpoints auditados.
    """
    result: dict[str, Any] = {}
    for key, value in data.items():
        if key in SENSITIVE_FIELDS:
            result[key] = _REDACTED
        elif isinstance(value, dict):
            result[key] = _redact_sensitive(value)
        else:
            result[key] = value
    return result


def _serializar(value: Any) -> Any:
    """Converte um argumento em uma forma persistível no Firestore.

    Modelos Pydantic viram dict (sem campos de identidade sensíveis do usuário,
    que já são capturados à parte); tipos nativos passam direto; o restante é
    convertido para string para evitar valores não serializáveis.
    """
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if isinstance(value, dict):
        return {str(key): _serializar(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_serializar(item) for item in value]
    return str(value)


def _build_valor_entrada(
    func: Any,
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
) -> dict[str, Any]:
    """Extrai os argumentos nomeados da chamada via inspect, ignorando self e o usuário."""
    try:
        bound = inspect.signature(func).bind_partial(*args, **kwargs)
    except TypeError:
        return {}

    raw = {
        name: _serializar(value)
        for name, value in bound.arguments.items()
        if name != "self" and not isinstance(value, CurrentUser)
    }
    return _redact_sensitive(raw)


def _entity_name(func: Any) -> str | None:
    """Deriva o nome da entidade a partir do módulo da função (ex: student_service → student)."""
    module = inspect.getmodule(func)
    if module is None:
        return None

    short = module.__name__.rsplit(".", 1)[-1]
    for suffix in _ENTITY_SUFFIXES:
        if short.endswith(suffix):
            return short[: -len(suffix)]
    return short


def _build_recurso(
    func: Any,
    valor_entrada: dict[str, Any],
    result: Any,
) -> str | None:
    """Monta o path soft do recurso afetado (ex: students/aluno_001).

    Usa o primeiro argumento terminado em '_id'; na ausência (ex: criação),
    recorre ao 'id' presente no resultado da operação.
    """
    entity = _entity_name(func)

    id_value: Any = next(
        (
            value
            for name, value in valor_entrada.items()
            if name.endswith("_id") and isinstance(value, (str, int))
        ),
        None,
    )
    if id_value is None and isinstance(result, dict):
        id_value = result.get("id")

    if id_value is None:
        return entity
    return f"{entity}/{id_value}" if entity else str(id_value)


def audit_operation(func):
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        if not aspect_config.AUDIT_ENABLED:
            return await func(*args, **kwargs)

        user = _find_user(args, kwargs)
        valor_entrada = _build_valor_entrada(func, args, kwargs)
        module = inspect.getmodule(func)
        modulo = module.__name__ if module else None

        repo = FirebaseRepository("audit_logs")

        started_at = datetime.now(timezone.utc)

        try:
            result = await func(*args, **kwargs)

            finished_at = datetime.now(timezone.utc)

            await repo.create(
                {
                    "usuario_id": user.uid if user else None,
                    "role": user.role if user else None,
                    "programa_id": user.programa_id if user else None,
                    "operacao": func.__name__,
                    "modulo": modulo,
                    "recurso": _build_recurso(func, valor_entrada, result),
                    "valor_entrada": valor_entrada,
                    "resultado_status": "sucesso",
                    "erro_mensagem": None,
                    "timestamp": finished_at,
                    "duracao_ms": int(
                        (finished_at - started_at).total_seconds() * 1000
                    ),
                },
            )

            return result

        except Exception as exc:
            finished_at = datetime.now(timezone.utc)

            await repo.create(
                {
                    "usuario_id": user.uid if user else None,
                    "role": user.role if user else None,
                    "programa_id": user.programa_id if user else None,
                    "operacao": func.__name__,
                    "modulo": modulo,
                    "recurso": _build_recurso(func, valor_entrada, None),
                    "valor_entrada": valor_entrada,
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
