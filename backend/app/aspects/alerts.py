"""
Aspecto A05 — Geração de Alertas e Notificações (After advice).

Responsabilidades:
- Implementar o decorador @trigger_alerts usando mecanismos nativos do Python, sem
  bibliotecas externas de AOP.
- After: verifica flag ALERTS_ENABLED em aspect_config. Extrai resultado da função original;
  determina destinatários (aluno_id → orientador_id via Firestore lookup). Monta documento
  Notification com {tipo, titulo, mensagem, destinatario_id, entidade_id, lida: false,
  timestamp} e persiste em notifications/{auto_id} no Firestore.
- Join points e alertas:
    - POST tasks/{id}/updates → notifica orientador (progresso registrado).
    - PATCH activities/{id}/validate → notifica aluno (aprovada|rejeitada).
    - PATCH extensions/{id}/approve → notifica aluno (resultado e novo prazo).
    - Delegação do A04 para prazo crítico → notifica aluno + orientador.
    - POST activities → notifica orientador (atividade submetida para validação).
- Frontend assina onSnapshot em notifications/ filtrado por destinatario_id para receber
  alertas em tempo real.
"""
"""
Aspecto A05 — Geração de Alertas e Notificações (After advice).

Preocupação transversal encapsulada:
    Disparar notificações para os usuários corretos após operações relevantes,
    sem que a lógica de negócio conheça o sistema de alertas.

Join Points:
    - ActivityService.submit_activity()   → notifica orientador após submissão do aluno
    - ActivityService.validate_activity() → notifica aluno após decisão da coordenação
    - ExtensionService.approve_extension()→ notifica aluno após decisão de prorrogação
    - WorkPlanService.add_update()        → notifica orientador após progresso do aluno
    - A04 (check_deadlines) delega aqui quando detecta prazo crítico

Advice (After):
    1. Verifica flag ALERTS_ENABLED em aspect_config; se False, retorna sem efeito.
    2. Extrai resultado da função original e IDs relevantes do contexto.
    3. Determina destinatários (aluno_id → orientador_id via Firestore lookup quando
       necessário).
    4. Monta documento Notification com {tipo, titulo, mensagem, destinatario_id,
       entidade_tipo, entidade_id, lida: false, timestamp, programa_id}.
    5. Persiste em notifications/{auto_id} no Firestore.
    6. Frontend usa onSnapshot filtrado por destinatario_id para receber em tempo real.

Weaving:
    Decorador @trigger_alerts aplicado após @requires_role e @audit_operation.
    Ordem canônica: @requires_role → @audit_operation → @trigger_alerts → def func(...)
"""

import asyncio
import functools
import logging
from datetime import datetime, timezone
from typing import Any, Callable, Optional

from backend.app.aspects.aspect_config import ALERTS_ENABLED
from backend.app.core.firebase import get_firestore_client

logger = logging.getLogger(__name__)

PROGRAMA_ID_DEFAULT = "prog_default"


def trigger_alerts(
    tipo: str,
    titulo: str,
    get_mensagem_fn: Callable[[Any, dict], str],
    get_destinatario_fn: Callable[[dict], Optional[str]],
    entidade_tipo: str,
    get_entidade_id_fn: Optional[Callable[[dict], Optional[str]]] = None,
) -> Callable:
    """
    Decorador After que dispara notificações no Firestore após a execução da função.

    Parâmetros:
    - tipo: identificador do tipo de notificação (ex: 'atividade_validada')
    - titulo: título fixo da notificação
    - get_mensagem_fn(result, kwargs): constrói a mensagem personalizada a partir
      do resultado da função e dos kwargs da chamada
    - get_destinatario_fn(kwargs): resolve o uid do destinatário a partir dos kwargs
    - entidade_tipo: tipo da entidade afetada (ex: 'activities')
    - get_entidade_id_fn(kwargs): extrai o ID da entidade dos kwargs (opcional)

    Advice: After — executa APÓS a função original, nunca interrompe o fluxo.
    Erros no advice são logados mas não propagados.
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Executa a função original primeiro (advice After)
            result = await func(*args, **kwargs)

            if not ALERTS_ENABLED:
                return result

            try:
                destinatario_id = get_destinatario_fn(kwargs)
                if not destinatario_id:
                    logger.warning(
                        "[A05] Destinatário não encontrado para notificação tipo='%s'",
                        tipo,
                    )
                    return result

                mensagem = get_mensagem_fn(result, kwargs)
                entidade_id = None
                if get_entidade_id_fn:
                    entidade_id = get_entidade_id_fn(kwargs)

                await _gravar_notificacao(
                    tipo=tipo,
                    titulo=titulo,
                    mensagem=mensagem,
                    destinatario_id=destinatario_id,
                    entidade_tipo=entidade_tipo,
                    entidade_id=entidade_id,
                )
            except Exception as exc:
                # A05 nunca derruba a operação principal
                logger.error("[A05] Falha ao disparar notificação tipo='%s': %s", tipo, exc)

            return result

        return wrapper
    return decorator


async def _gravar_notificacao(
    tipo: str,
    titulo: str,
    mensagem: str,
    destinatario_id: str,
    entidade_tipo: str,
    entidade_id: Optional[str],
) -> None:
    """Persiste o documento de notificação na coleção notifications/ do Firestore."""
    try:
        db = get_firestore_client()
        doc: dict[str, Any] = {
            "tipo": tipo,
            "titulo": titulo,
            "mensagem": mensagem,
            "destinatario_id": destinatario_id,
            "entidade_tipo": entidade_tipo,
            "entidade_id": entidade_id,
            "lida": False,
            "timestamp": datetime.now(timezone.utc),
            "programa_id": PROGRAMA_ID_DEFAULT,
        }
        db.collection("notifications").add(doc)
        logger.debug(
            "[A05] Notificação gravada: tipo=%s destinatario=%s entidade_id=%s",
            tipo,
            destinatario_id,
            entidade_id,
        )
    except Exception as exc:
        logger.error("[A05] Erro ao gravar notificação no Firestore: %s", exc)


async def disparar_alerta_prazo(
    destinatario_id: str,
    nome_aluno: str,
    tipo_prazo: str,
    dias_restantes: int,
    student_id: str,
) -> None:
    """
    Ponto de entrada para o aspecto A04 delegar alertas de prazo ao A05.

    Chamado por @check_deadlines quando detecta prazo crítico.
    Não é um decorador — é uma função direta usada via delegação entre aspectos.

    Parâmetros:
    - destinatario_id: uid do aluno ou orientador a notificar
    - nome_aluno: nome do aluno para interpolação da mensagem
    - tipo_prazo: 'qualificacao' | 'final'
    - dias_restantes: quantidade de dias restantes
    - student_id: ID do aluno no Firestore (usado como entidade_id)
    """
    if not ALERTS_ENABLED:
        return

    tipo_label = "qualificação" if tipo_prazo == "qualificacao" else "entrega final"
    await _gravar_notificacao(
        tipo="prazo_critico",
        titulo="Prazo crítico",
        mensagem=(
            f"Atenção: prazo de {tipo_label} de {nome_aluno} "
            f"vence em {dias_restantes} dia(s)."
        ),
        destinatario_id=destinatario_id,
        entidade_tipo="students",
        entidade_id=student_id,
    )