"""
Aspecto A05 — Geração de Alertas e Notificações (After advice).

Responsabilidades:
- Implementar o decorador @trigger_alerts(build) usando mecanismos nativos do Python, sem
  bibliotecas externas de AOP.
- After: executa a função original; se ALERTS_ENABLED, chama o `build` (síncrono ou
  assíncrono) com (resultado, args, kwargs) para obter a(s) notificação(ões) a emitir;
  normaliza cada documento (default lida=False e timestamp=agora) e persiste em
  notifications/{auto_id}. Se a função original levantar exceção, nenhum alerta é disparado.
- O `build` é fornecido por quem aplica o aspecto e encapsula a lógica específica do join
  point (destinatário via lookup no Firestore, tipo, título e mensagem). Assim a lógica de
  negócio permanece livre do sistema de alertas, e a fiação a cada endpoint disparador
  (tasks/updates, activities/validate, extensions/approve, prazo crítico) ocorre nas issues
  desses domínios.
- Frontend assina onSnapshot em notifications/ filtrado por destinatario_id para receber
  alertas em tempo real.
"""

from __future__ import annotations

import functools
import inspect
import logging
from datetime import datetime, timezone
from typing import Any, Callable, Optional

from backend.app.aspects import aspect_config
from backend.app.core.firebase import get_firestore_client

logger = logging.getLogger(__name__)

_COLLECTION = "notifications"


class FirebaseRepository:
    """Repositório Firestore para notificações (exposto para monkeypatch em testes)."""

    def __init__(self, collection: str) -> None:
        self.collection = collection

    async def create(self, data: dict[str, Any]) -> str:
        try:
            db = get_firestore_client()
            _, doc_ref = db.collection(self.collection).add(data)
            return doc_ref.id
        except Exception as exc:
            logger.error("[A05] Falha ao gravar notificação: %s", exc)
            return ""


def trigger_alerts(build: Callable) -> Callable:
    """Decorador After que dispara notificações após a execução da função.

    Args:
        build: Callable (síncrono ou assíncrono) com assinatura
               (result, args, kwargs) -> dict | list[dict] | None.
               Retorna um ou mais documentos de notificação, ou None para não disparar.

    Advice: After — executa APÓS a função original, nunca interrompe o fluxo.
    Erros no advice são logados mas não propagados.
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            result = await func(*args, **kwargs)

            if not aspect_config.ALERTS_ENABLED:
                return result

            try:
                raw = build(result, args, kwargs)
                if inspect.isawaitable(raw):
                    raw = await raw

                if raw is None:
                    return result

                specs = raw if isinstance(raw, list) else [raw]

                repo = FirebaseRepository(_COLLECTION)
                for spec in specs:
                    if not spec:
                        continue
                    doc = {
                        **spec,
                        "lida": spec.get("lida", False),
                        "timestamp": spec.get("timestamp", datetime.now(timezone.utc)),
                    }
                    await repo.create(doc)
                    logger.debug(
                        "[A05] Notificação gravada: tipo=%s destinatario=%s",
                        spec.get("tipo"),
                        spec.get("destinatario_id"),
                    )
            except Exception as exc:
                logger.error("[A05] Falha ao disparar notificação: %s", exc)

            return result

        return wrapper

    return decorator


async def disparar_alerta_prazo(
    destinatario_id: str,
    nome_aluno: str,
    tipo_prazo: str,
    dias_restantes: int,
    student_id: str,
) -> None:
    """Ponto de entrada para o aspecto A04 delegar alertas de prazo ao A05.

    Chamado por @check_deadlines quando detecta prazo crítico.
    Não é um decorador — é uma função direta usada via delegação entre aspectos.

    Args:
        destinatario_id: uid do aluno ou orientador a notificar.
        nome_aluno: nome do aluno para interpolação da mensagem.
        tipo_prazo: 'qualificacao' | 'final'.
        dias_restantes: quantidade de dias restantes.
        student_id: ID do aluno no Firestore (usado como entidade_id).
    """
    if not aspect_config.ALERTS_ENABLED:
        return

    tipo_label = "qualificação" if tipo_prazo == "qualificacao" else "entrega final"
    doc: dict[str, Any] = {
        "tipo": "prazo_critico",
        "titulo": "Prazo crítico",
        "mensagem": (
            f"Atenção: prazo de {tipo_label} de {nome_aluno} "
            f"vence em {dias_restantes} dia(s)."
        ),
        "destinatario_id": destinatario_id,
        "entidade_tipo": "students",
        "entidade_id": student_id,
        "lida": False,
        "timestamp": datetime.now(timezone.utc),
    }

    try:
        repo = FirebaseRepository(_COLLECTION)
        await repo.create(doc)
        logger.debug(
            "[A05] Alerta de prazo gravado: tipo_prazo=%s destinatario=%s",
            tipo_prazo,
            destinatario_id,
        )
    except Exception as exc:
        logger.error("[A05] Falha ao gravar alerta de prazo: %s", exc)

        # backend/app/aspects/alerts.py  — acrescentar ao final do arquivo

def _build_notification_payload(
    result: Any,
    args: tuple,
    kwargs: dict,
) -> dict | None:
    """Builder A05 para o domínio de Prorrogações (extensions).

    Usado como argumento de @trigger_alerts nos join points:
      - POST   /api/v1/extensions          (create_extension)
      - PATCH  /api/v1/extensions/.../approve (decide_extension)

    Regras de negócio:
      - Criação  (status PENDENTE)  → avisa o orientador que há nova solicitação.
      - Aprovação/Indeferimento     → avisa o aluno sobre a decisão.
      - Qualquer outro status       → sem notificação (retorna None).

    O destinatário é extraído do próprio ExtensionResponse para não
    realizar lookups adicionais no Firestore dentro do advice.
    """
    try:
        status = getattr(result, "status", None)
        if status is None:
            return None

        status_value = status.value if hasattr(status, "value") else str(status)

        if status_value == "pendente":
            destinatario_id = getattr(result, "orientador_id", None)
            if not destinatario_id:
                return None
            student_id = getattr(result, "student_id", "")
            return {
                "tipo": "nova_prorrogacao",
                "titulo": "Nova solicitação de prorrogação",
                "mensagem": (
                    "Um aluno submeteu uma solicitação de prorrogação de prazo "
                    "aguardando seu parecer técnico."
                ),
                "destinatario_id": destinatario_id,
                "entidade_tipo": "extensions",
                "entidade_id": getattr(result, "id", ""),
                "student_id": student_id,
            }

        if status_value in ("aprovada", "reprovada", "indeferida"):
            destinatario_id = getattr(result, "student_id", None)
            if not destinatario_id:
                return None
            decisao = "deferida" if status_value == "aprovada" else "indeferida"
            return {
                "tipo": "decisao_prorrogacao",
                "titulo": "Decisão sobre sua prorrogação",
                "mensagem": (
                    f"Sua solicitação de prorrogação foi {decisao} pela coordenação."
                ),
                "destinatario_id": destinatario_id,
                "entidade_tipo": "extensions",
                "entidade_id": getattr(result, "id", ""),
            }

    except Exception as exc:  # pragma: no cover
        logger.error("[A05] _build_notification_payload: erro inesperado: %s", exc)

    return None
