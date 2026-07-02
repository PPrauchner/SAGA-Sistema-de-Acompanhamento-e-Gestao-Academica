"""
Modelos Pydantic de resposta para a consulta de logs de auditoria (aspecto A02).

Responsabilidades:
- Definir AuditLogResponse mapeando o documento da coleção audit_logs/ gerado pelo
  decorador @audit_operation: usuario_id, role, programa_id, operacao, modulo, recurso,
  valor_entrada, resultado_status, erro_mensagem, timestamp e duracao_ms.
- Definir AuditLogPage como envelope de paginação retornado por GET /api/v1/audit-logs,
  com items, page, page_size e total.
- Campos derivados do aspecto são opcionais para tolerar documentos legados anteriores ao
  enriquecimento do advice (sem modulo/recurso/valor_entrada).
- usuario_nome não é campo do documento: é resolvido pelo AuditService no read path a
  partir de usuario_id (o id permanece a chave canônica persistida).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel

ResultadoStatus = Literal["sucesso", "erro"]


class AuditLogResponse(BaseModel):
    """Um registro imutável de auditoria de operação."""

    id: str

    usuario_id: str | None = None
    usuario_nome: str | None = None
    role: str | None = None
    programa_id: str | None = None

    operacao: str | None = None
    modulo: str | None = None
    recurso: str | None = None
    valor_entrada: dict[str, Any] | None = None

    resultado_status: ResultadoStatus | None = None
    erro_mensagem: str | None = None

    timestamp: datetime | None = None
    duracao_ms: int | None = None


class AuditLogPage(BaseModel):
    """Página de logs de auditoria retornada pela consulta paginada."""

    items: list[AuditLogResponse]
    page: int
    page_size: int
    total: int
