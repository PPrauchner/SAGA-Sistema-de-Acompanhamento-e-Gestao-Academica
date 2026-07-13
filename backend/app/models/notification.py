"""
Modelos Pydantic para a entidade Notification (aspecto A05).

Responsabilidades:
- Definir NotificationTipo com os tipos válidos de notificação emitidos pelo aspecto
  @trigger_alerts (progresso_task, atividade_validada, prorrogacao_aprovada,
  prorrogacao_rejeitada, prazo_critico, atividade_submetida).
- Definir NotificationResponse mapeando o documento da coleção notifications/ — schema
  canônico produzido pelo aspecto e lido em tempo real pelo frontend via onSnapshot.
- Definir MarkReadResponse, retorno do PATCH /notifications/{id}/read.
- A escrita em notifications/ é exclusiva do aspecto A05; o backend só expõe a marcação
  como lida.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel

NotificationTipo = Literal[
    "progresso_task",
    "atividade_validada",
    "prorrogacao_aprovada",
    "prorrogacao_rejeitada",
    "prazo_critico",
    "atividade_submetida",
]


class NotificationResponse(BaseModel):
    """Schema canônico de um documento da coleção notifications/."""

    id: str

    tipo: NotificationTipo | str
    titulo: str
    mensagem: str

    destinatario_id: str
    entidade_tipo: str | None = None
    entidade_id: str | None = None

    lida: bool = False
    timestamp: datetime | None = None
    programa_id: str | None = None


class MarkReadResponse(BaseModel):
    """Confirmação da marcação de uma notificação como lida."""

    id: str
    lida: bool
    message: str
