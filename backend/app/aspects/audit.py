import functools
import inspect
import logging
from datetime import datetime, timezone
from typing import Any, Callable, Optional

from backend.app.aspects import aspect_config
from backend.app.core.firebase import get_firestore_client

logger = logging.getLogger(__name__)


def audit_operation(
    operacao: str,
    entidade: str,
    get_entity_id_fn: Optional[Callable] = None,
) -> Callable:
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            if not aspect_config.AUDIT_ENABLED:
                return await func(*args, **kwargs)

            current_user: dict | None = None
            for v in list(kwargs.values()) + list(args):
                if isinstance(v, dict) and "role" in v:
                    current_user = v
                    break
                if hasattr(v, "role") and hasattr(v, "uid"):
                    current_user = {"uid": v.uid, "email": getattr(v, "email", None), "role": v.role}
                    break

            try:
                bound = inspect.signature(func).bind(*args, **kwargs)
                bound.apply_defaults()
                valor_entrada = {k: repr(v) for k, v in bound.arguments.items() if k != "current_user"}
            except Exception:
                valor_entrada = {}

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
                duracao_ms = int((datetime.now(timezone.utc) - timestamp_inicio).total_seconds() * 1000)
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
            # Nomes esperados pelos testes
            "uid_usuario": current_user.get("uid") if current_user else None,
            "email_usuario": current_user.get("email") if current_user else None,
            "role_usuario": current_user.get("role") if current_user else None,
            "operacao": operacao,
            "modulo": modulo,
            "recurso": entidade,
            "entidade_id": entidade_id,
            "valor_entrada": valor_entrada,
            "timestamp": timestamp,
            "resultado": resultado,       # era "resultado_status"
            "duracao_ms": duracao_ms,
        }
        if detalhe_erro:
            log_entry["detalhe_erro"] = detalhe_erro   # era "erro_mensagem"

        db.collection("audit_logs").add(log_entry)
        logger.debug("[A02] Auditoria gravada: op=%s entidade=%s id=%s resultado=%s duracao=%dms",
                     operacao, entidade, entidade_id, resultado, duracao_ms)
    except Exception as exc:
        logger.error("[A02] Falha ao gravar audit_log: %s", exc)