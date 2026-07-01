"""
Router FastAPI para o endpoint de consulta paginada de logs de auditoria.

Responsabilidades:
- GET /api/v1/audit-logs: retorna lista paginada de documentos da coleção audit_logs/ com
  filtros opcionais por usuario_id, operacao, modulo, data_inicio, data_fim e
  resultado_status. Suporta paginação via parâmetros page e page_size (max: 100). Dados
  gerados pelo aspecto A02 (@audit_operation). Autorizado para coordenação (visão total) e
  orientador (escopado pelo service aos logs dos seus orientandos).
  Alimenta a AuditPage e a timeline do OrientadorDashboard com dados reais.
"""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Query

from backend.app.aspects.authorization import requires_role
from backend.app.core.auth import CurrentUser, get_current_user
from backend.app.models.audit import AuditLogPage, ResultadoStatus
from backend.app.services.audit_service import AuditService

router = APIRouter()

service = AuditService()


@router.get("/audit-logs")
@requires_role("coordenacao", "orientador")
async def list_audit_logs(
    usuario_id: str | None = None,
    operacao: str | None = None,
    modulo: str | None = None,
    resultado_status: ResultadoStatus | None = None,
    data_inicio: datetime | None = None,
    data_fim: datetime | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user: CurrentUser = Depends(get_current_user),
) -> AuditLogPage:
    return await service.list_audit_logs(
        usuario_id=usuario_id,
        operacao=operacao,
        modulo=modulo,
        resultado_status=resultado_status,
        data_inicio=data_inicio,
        data_fim=data_fim,
        page=page,
        page_size=page_size,
        user=user,
    )
