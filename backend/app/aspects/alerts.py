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
from backend.app.repositories.firebase_repository import FirebaseRepository as FirestoreRepository

logger = logging.getLogger(__name__)

_COLLECTION = "notifications"
UserPreferencesRepository = FirestoreRepository

_DEFAULT_NOTIFICATION_PREFERENCES = {
    "email": True,
    "in_app": True,
    "work_plan": True,
    "transfers": True,
    "activities": True,
    "extensions": True,
}


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


def _preference_key_for_notification(spec: dict[str, Any]) -> str | None:
    tipo = str(spec.get("tipo", ""))
    entidade_tipo = str(spec.get("entidade_tipo", ""))

    if tipo in {"progresso_task", "prazo_critico"} or entidade_tipo == "work_plan":
        return "work_plan"
    if tipo.startswith("transferencia_") or entidade_tipo in {"transfer", "transfers"}:
        return "transfers"
    if tipo in {"atividade_validada", "atividade_submetida"} or entidade_tipo == "activities":
        return "activities"
    if tipo == "prorrogacao_aprovada" or entidade_tipo == "extensions":
        return "extensions"
    return None


async def _notification_enabled(spec: dict[str, Any]) -> bool:
    destinatario_id = spec.get("destinatario_id")
    if not destinatario_id:
        return True

    try:
        user_doc = await UserPreferencesRepository("users").get(destinatario_id)
    except Exception as exc:
        logger.error("[A05] Falha ao ler preferencias de notificacao: %s", exc)
        return True

    preferences = {
        **_DEFAULT_NOTIFICATION_PREFERENCES,
        **((user_doc or {}).get("notification_preferences") or {}),
    }
    if not preferences.get("in_app", True):
        return False

    preference_key = _preference_key_for_notification(spec)
    return preference_key is None or preferences.get(preference_key, True)


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
                    if not await _notification_enabled(doc):
                        logger.debug(
                            "[A05] Notificacao ignorada por preferencia: tipo=%s destinatario=%s",
                            spec.get("tipo"),
                            spec.get("destinatario_id"),
                        )
                        continue
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
        if not await _notification_enabled(doc):
            logger.debug(
                "[A05] Alerta de prazo ignorado por preferencia: destinatario=%s",
                destinatario_id,
            )
            return

        repo = FirebaseRepository(_COLLECTION)
        await repo.create(doc)
        logger.debug(
            "[A05] Alerta de prazo gravado: tipo_prazo=%s destinatario=%s",
            tipo_prazo,
            destinatario_id,
        )
    except Exception as exc:
        logger.error("[A05] Falha ao gravar alerta de prazo: %s", exc)
