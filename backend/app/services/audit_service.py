"""
Serviço de leitura dos logs de auditoria (aspecto A02).

Responsabilidades:
- list_audit_logs(): lê a coleção audit_logs/, aplica filtros opcionais (usuario_id,
  operacao, modulo, resultado_status, data_inicio, data_fim), ordena do mais recente ao
  mais antigo e devolve uma página (AuditLogPage) com base em page/page_size.
- Não escreve em audit_logs/ — a escrita é exclusiva do aspecto @audit_operation.
- A paginação e os filtros são aplicados em memória: a coleção é apenas anexada (nunca
  deletada) e, no MVP single-tenant, o volume é compatível com leitura completa.
"""

from __future__ import annotations

from datetime import datetime, timezone

from backend.app.models.audit import AuditLogPage, AuditLogResponse
from backend.app.repositories.firebase_repository import FirebaseRepository

_MIN_TIMESTAMP = datetime.min.replace(tzinfo=timezone.utc)


class AuditService:
    """Serviço de consulta dos logs de auditoria gerados pelo aspecto A02."""

    def __init__(self) -> None:
        self._repo = FirebaseRepository("audit_logs")

    @staticmethod
    def _matches(
        log: dict,
        *,
        usuario_id: str | None,
        operacao: str | None,
        modulo: str | None,
        resultado_status: str | None,
        data_inicio: datetime | None,
        data_fim: datetime | None,
    ) -> bool:
        if usuario_id and log.get("usuario_id") != usuario_id:
            return False
        if operacao and log.get("operacao") != operacao:
            return False
        if modulo and log.get("modulo") != modulo:
            return False
        if resultado_status and log.get("resultado_status") != resultado_status:
            return False

        timestamp = log.get("timestamp")
        if (data_inicio or data_fim) and timestamp is None:
            return False
        if timestamp is not None and timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)
        if data_inicio:
            dt_inicio = data_inicio if data_inicio.tzinfo else data_inicio.replace(tzinfo=timezone.utc)
            if timestamp < dt_inicio:
                return False
        if data_fim:
            dt_fim = data_fim if data_fim.tzinfo else data_fim.replace(tzinfo=timezone.utc)
            if timestamp > dt_fim:
                return False

        return True

    async def list_audit_logs(
        self,
        *,
        usuario_id: str | None = None,
        operacao: str | None = None,
        modulo: str | None = None,
        resultado_status: str | None = None,
        data_inicio: datetime | None = None,
        data_fim: datetime | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> AuditLogPage:
        logs = await self._repo.list_all()

        filtered = [
            log
            for log in logs
            if self._matches(
                log,
                usuario_id=usuario_id,
                operacao=operacao,
                modulo=modulo,
                resultado_status=resultado_status,
                data_inicio=data_inicio,
                data_fim=data_fim,
            )
        ]

        filtered.sort(
            key=lambda log: log.get("timestamp") or _MIN_TIMESTAMP,
            reverse=True,
        )

        start = (page - 1) * page_size
        window = filtered[start : start + page_size]

        return AuditLogPage(
            items=[AuditLogResponse.model_validate(log) for log in window],
            page=page,
            page_size=page_size,
            total=len(filtered),
        )
