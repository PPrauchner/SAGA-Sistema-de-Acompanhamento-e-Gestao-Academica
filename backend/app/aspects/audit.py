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
"""
A02 — Aspecto de Auditoria

Advice: Around
Mecanismo: Decorador @audit_operation + inspect

Join Points:
- Qualquer operação de escrita (create, update, validate, delete)

Conceitos AOP:
- Join Point: chamada da função decorada
- Advice (Around): captura estado antes e depois, registra log no Firestore
- Weaving: aplicado via decorador em tempo de definição
"""

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
    """
    Decorador Around que registra a operação no log de auditoria do Firestore.

    Parâmetros:
    - operacao: nome da operação (ex: "parecer_orientador", "aprovar_atividade")
    - entidade: nome da coleção/entidade (ex: "activities")
    - get_entity_id_fn: função opcional (kwargs) -> str para extrair o ID da entidade

    Campos gravados em audit_logs/{auto_id}:
    - uid_usuario, email_usuario, role_usuario
    - operacao, entidade, entidade_id
    - timestamp
    - resultado: "sucesso" | "erro"
    - detalhe_erro (se houver)
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            if not aspect_config.AUDIT_ENABLED:
                return await func(*args, **kwargs)

            # Extrai current_user dos kwargs/args
            current_user: dict | None = None
            for v in list(kwargs.values()) + list(args):
                if isinstance(v, dict) and "role" in v:
                    current_user = v
                    break

            entity_id = None
            if get_entity_id_fn:
                try:
                    res = get_entity_id_fn(kwargs)
                    if inspect.isawaitable(res):
                        entity_id = await res
                    else:
                        entity_id = res
                except Exception:
                    pass

            timestamp = datetime.now(timezone.utc)
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
                await _gravar_audit_log(
                    current_user=current_user,
                    operacao=operacao,
                    entidade=entidade,
                    entidade_id=entity_id,
                    timestamp=timestamp,
                    resultado=resultado,
                    detalhe_erro=detalhe_erro,
                )

            return result

        return wrapper
    return decorator


async def _gravar_audit_log(
    current_user: dict | None,
    operacao: str,
    entidade: str,
    entidade_id: str | None,
    timestamp: datetime,
    resultado: str,
    detalhe_erro: str | None,
) -> None:
    try:
        db = get_firestore_client()
        log_entry: dict[str, Any] = {
            "uid_usuario": current_user.get("uid") if current_user else None,
            "email_usuario": current_user.get("email") if current_user else None,
            "role_usuario": current_user.get("role") if current_user else None,
            "operacao": operacao,
            "entidade": entidade,
            "entidade_id": entidade_id,
            "timestamp": timestamp,
            "resultado": resultado,
        }
        if detalhe_erro:
            log_entry["detalhe_erro"] = detalhe_erro

        db.collection("audit_logs").add(log_entry)
        logger.debug(
            "[A02] Auditoria gravada: op=%s entidade=%s id=%s resultado=%s",
            operacao, entidade, entidade_id, resultado,
        )
    except Exception as exc:
        # Auditoria nunca deve derrubar a operação principal
        logger.error("[A02] Falha ao gravar audit_log: %s", exc)