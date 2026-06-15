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

import functools
import inspect
import logging
from datetime import datetime, timezone
from typing import Any, Callable, Optional

from backend.app.aspects.aspect_config import AUDIT_ENABLED
from backend.app.core.firebase import get_firestore_client

logger = logging.getLogger(__name__)


def audit_operation(
    operacao: str,
    entidade: str,
    get_entity_id_fn: Optional[Callable] = None,
) -> Callable:
    """
    Decorador Around que registra a operação no log de auditoria do Firestore.

    Parâmetros:
    - operacao: nome da operação (ex: "parecer_orientador", "aprovar_atividade")
    - entidade: nome da coleção/entidade (ex: "activities")
    - get_entity_id_fn: função opcional (kwargs) -> str para extrair o ID da entidade

    Campos gravados em audit_logs/{auto_id} (spec 02):
    - usuario_id, email_usuario, role
    - operacao, modulo, recurso, entidade_id
    - valor_entrada (parâmetros capturados via inspect.signature)
    - timestamp, duracao_ms
    - resultado_status: "sucesso" | "erro"
    - erro_mensagem (se houver)
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            if not AUDIT_ENABLED:
                return await func(*args, **kwargs)

            # Extrai current_user dos kwargs/args
            current_user: dict | None = None
            for v in list(kwargs.values()) + list(args):
                if isinstance(v, dict) and "role" in v:
                    current_user = v
                    break
                if hasattr(v, "role") and hasattr(v, "uid"):
                    current_user = {
                        "uid": v.uid,
                        "email": getattr(v, "email", None),
                        "role": v.role,
                    }
                    break

            # Captura parâmetros de entrada via inspect.signature (spec 02)
            try:
                bound = inspect.signature(func).bind(*args, **kwargs)
                bound.apply_defaults()
                valor_entrada = {
                    k: repr(v)
                    for k, v in bound.arguments.items()
                    if k != "current_user"
                }
            except Exception:
                valor_entrada = {}

            # Captura módulo via inspect.getmodule (spec 02)
            modulo = inspect.getmodule(func)
            modulo_nome = modulo.__name__ if modulo else "desconhecido"

            entity_id = None
            if get_entity_id_fn:
                try:
                    entity_id = get_entity_id_fn(kwargs)
                except Exception:
                    pass

            timestamp_inicio = datetime.now(timezone.utc)
            resultado = "sucesso"
            detalhe_erro = None
            result = None

            try:
                result = await func(*args, **kwargs)
            except Exception as exc:
                resultado = "erro"
                detalhe_erro = str(exc)
                raise
            finally:
                duracao_ms = int(
                    (datetime.now(timezone.utc) - timestamp_inicio).total_seconds() * 1000
                )
                await _gravar_audit_log(
                    current_user=current_user,
                    operacao=operacao,
                    entidade=entidade,
                    entidade_id=entity_id,
                    modulo=modulo_nome,
                    valor_entrada=valor_entrada,
                    timestamp=timestamp_inicio,
                    resultado=resultado,
                    detalhe_erro=detalhe_erro,
                    duracao_ms=duracao_ms,
                )

            return result

        return wrapper
    return decorator


async def _gravar_audit_log(
    current_user: dict | None,
    operacao: str,
    entidade: str,
    entidade_id: str | None,
    modulo: str,
    valor_entrada: dict,
    timestamp: datetime,
    resultado: str,
    detalhe_erro: str | None,
    duracao_ms: int,
) -> None:
    try:
        db = get_firestore_client()
        log_entry: dict[str, Any] = {
            "usuario_id": current_user.get("uid") if current_user else None,
            "email_usuario": current_user.get("email") if current_user else None,
            "role": current_user.get("role") if current_user else None,
            "operacao": operacao,
            "modulo": modulo,
            "recurso": entidade,
            "entidade_id": entidade_id,
            "valor_entrada": valor_entrada,
            "timestamp": timestamp,
            "resultado_status": resultado,
            "duracao_ms": duracao_ms,
        }
        if detalhe_erro:
            log_entry["erro_mensagem"] = detalhe_erro

        db.collection("audit_logs").add(log_entry)
        logger.debug(
            "[A02] Auditoria gravada: op=%s entidade=%s id=%s resultado=%s duracao=%dms",
            operacao, entidade, entidade_id, resultado, duracao_ms,
        )
    except Exception as exc:
        # Auditoria nunca deve derrubar a operação principal
        logger.error("[A02] Falha ao gravar audit_log: %s", exc)