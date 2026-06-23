"""
Aspecto A02 – Auditoria de Operações.

Responsabilidades:
- Registrar no Firestore toda operação sensível executada nos endpoints.
- Capturar autoria (usuario_id, role, programa_id), nome da operação,
  módulo, recurso afetado, argumentos de entrada e resultado.
- Permitir desativação via aspect_config.AUDIT_ENABLED sem alterar endpoints.

Join Point : qualquer endpoint FastAPI decorado com @audit_operation.
Advice     : Around – envolve a execução da função original.
Weaving    : decorador Python aplicado manualmente sobre funções de negócio.
"""

from __future__ import annotations

import functools
import inspect
import logging
from datetime import datetime, timezone
from typing import Any, Callable

from backend.app.aspects import aspect_config
from backend.app.core.firebase import get_firestore_client

logger = logging.getLogger(__name__)

_COLLECTION = "audit_logs"
SENSITIVE_FIELDS: frozenset[str] = frozenset(
    {"password", "senha", "token", "secret", "api_key", "private_key", "refresh_token"}
)

_REDACTED = "***"


SENSITIVE_FIELDS: frozenset[str] = frozenset(
    {"password", "senha", "token", "secret", "api_key", "private_key", "refresh_token"}
)

_REDACTED = "***"

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
    """Monta o path soft do recurso afetado (ex: students/aluno_001)."""

class FirebaseRepository:
    """Repositório Firestore para registros de auditoria."""

    def __init__(self, collection: str) -> None:
        self.collection = collection

    async def create(self, data: dict[str, Any]) -> str:
        try:
            db = get_firestore_client()
            _, doc_ref = db.collection(self.collection).add(data)
            return doc_ref.id
        except Exception as exc:
            logger.error("[A02] Falha ao gravar audit_log: %s", exc)
            return ""


def _extrair_usuario(args: tuple, kwargs: dict) -> dict[str, Any]:
    candidatos = list(kwargs.values()) + list(args)
    for v in candidatos:
        if isinstance(v, dict) and "role" in v:
            return {
                "usuario_id": v.get("uid", ""),
                "role": v.get("role", ""),
                "programa_id": v.get("programa_id", ""),
            }
        if hasattr(v, "role") and hasattr(v, "uid"):
            return {
                "usuario_id": v.uid,
                "role": v.role,
                "programa_id": getattr(v, "programa_id", ""),
            }
    return {"usuario_id": "", "role": "", "programa_id": ""}


def _extrair_recurso_dos_args(
    sig: inspect.Signature,
    bound: inspect.BoundArguments,
) -> str | None:
    for nome, valor in bound.arguments.items():
        if nome.endswith("_id") and isinstance(valor, str):
            return f"{nome}/{valor}"
    return None


def _extrair_recurso_do_resultado(resultado: Any) -> str | None:
    if isinstance(resultado, dict) and "id" in resultado:
        return f"id/{resultado['id']}"
    if hasattr(resultado, "id"):
        return f"id/{resultado.id}"
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


def _extrair_valor_entrada(
    sig: inspect.Signature,
    bound: inspect.BoundArguments,
) -> dict[str, Any]:
    resultado: dict[str, Any] = {}
    for nome, valor in bound.arguments.items():
        if isinstance(valor, dict) and "role" in valor:
            continue
        if hasattr(valor, "role") and hasattr(valor, "uid"):
            continue
        resultado[nome] = valor
    # Redação A02 (portada da development): nunca persistir segredos no audit_log.
    return _redact_sensitive(resultado)


def audit_operation(
    func: Callable | None = None,
    *,
    operacao: str | None = None,
    entidade: str | None = None,
) -> Callable:
    """Aspecto A02 – suporta uso bare e parametrizado.

    Uso bare         : @audit_operation
    Uso parametrizado: @audit_operation(operacao="nome", entidade="recurso")
    """

    def _decorator(fn: Callable) -> Callable:
        sig = inspect.signature(fn)
        modulo = inspect.getmodule(fn)
        modulo_nome = modulo.__name__ if modulo else "desconhecido"
        operacao_nome = operacao or fn.__name__

        @functools.wraps(fn)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            if not aspect_config.AUDIT_ENABLED:
                return await fn(*args, **kwargs)

            usuario = _extrair_usuario(args, kwargs)

            try:
                bound = sig.bind(*args, **kwargs)
                bound.apply_defaults()
            except TypeError:
                bound = None

            valor_entrada: dict[str, Any] = {}
            if bound:
                valor_entrada = _extrair_valor_entrada(sig, bound)

            recurso_dos_args: str | None = None
            if bound:
                recurso_dos_args = _extrair_recurso_dos_args(sig, bound)

            resultado_status = "sucesso"
            erro_mensagem: str | None = None
            result: Any = None

            try:
                result = await fn(*args, **kwargs)
            except Exception as exc:
                resultado_status = "erro"
                erro_mensagem = str(exc)
                raise
            finally:
                recurso = recurso_dos_args
                if recurso is None and result is not None:
                    recurso = _extrair_recurso_do_resultado(result)
                if recurso is None:
                    recurso = entidade or operacao_nome

                registro: dict[str, Any] = {
                    **usuario,
                    "operacao": operacao_nome,
                    "modulo": modulo_nome,
                    "recurso": recurso,
                    "valor_entrada": valor_entrada,
                    "resultado_status": resultado_status,
                    "timestamp": datetime.now(timezone.utc),
                }
                if erro_mensagem is not None:
                    registro["erro_mensagem"] = erro_mensagem

                repo = FirebaseRepository(_COLLECTION)
                await repo.create(registro)

                logger.debug(
                    "[A02] Auditoria: op=%s recurso=%s resultado=%s",
                    operacao_nome,
                    recurso,
                    resultado_status,
                )

            return result

        return wrapper

    if func is not None:
        return _decorator(func)
    return _decorator