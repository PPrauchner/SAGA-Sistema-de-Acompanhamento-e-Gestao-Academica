"""Router FastAPI para transferencia de orientandos."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from backend.app.aspects.alerts import trigger_alerts
from backend.app.aspects.audit import audit_operation
from backend.app.aspects.authorization import requires_role
from backend.app.aspects.history import track_history
from backend.app.core.auth import CurrentUser, get_current_user
from backend.app.models.transfer import DirectTransferRequest, DirectTransferResponse
from backend.app.services.transfer_service import TransferService

router = APIRouter()

service = TransferService()


def _transfer_notification(
    destinatario_id: str | None,
    titulo: str,
    mensagem: str,
    result: dict[str, Any],
) -> dict[str, Any] | None:
    if not destinatario_id:
        return None

    return {
        "tipo": "transferencia_orientador",
        "titulo": titulo,
        "mensagem": mensagem,
        "destinatario_id": destinatario_id,
        "entidade_tipo": "student",
        "entidade_id": result["student_id"],
        "programa_id": result.get("programa_id"),
    }


def _build_direct_transfer_alerts(
    result: dict[str, Any],
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
) -> list[dict[str, Any]]:
    student_name = result.get("student_nome") or "Aluno"
    destination_name = result.get("orientador_destino_nome") or "novo orientador"

    alerts = [
        _transfer_notification(
            result.get("orientador_origem_uid"),
            "Orientando transferido",
            f"{student_name} foi transferido para {destination_name}.",
            result,
        ),
        _transfer_notification(
            result.get("orientador_destino_uid"),
            "Novo orientando recebido",
            f"{student_name} agora esta sob sua orientacao.",
            result,
        ),
        _transfer_notification(
            result.get("student_uid"),
            "Orientador alterado",
            f"Sua orientacao foi transferida para {destination_name}.",
            result,
        ),
    ]

    if result.get("pending_cancelled"):
        alerts.append(
            _transfer_notification(
                result.get("pending_solicitante_id"),
                "Solicitacao de transferencia cancelada",
                "Uma solicitacao pendente foi cancelada porque a coordenacao realizou a transferencia direta.",
                result,
            ),
        )

    return [alert for alert in alerts if alert is not None]


@router.post("/transfers/direct", response_model=DirectTransferResponse)
@requires_role("coordenacao")
@audit_operation
@track_history
@trigger_alerts(_build_direct_transfer_alerts)
async def direct_transfer(
    body: DirectTransferRequest,
    user: CurrentUser = Depends(get_current_user),
) -> dict[str, Any]:
    return await service.direct_transfer(body, user)
