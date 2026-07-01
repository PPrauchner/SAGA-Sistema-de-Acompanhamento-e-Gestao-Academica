"""Router do fluxo de transferencia de coordenacao."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, status

from backend.app.aspects.alerts import trigger_alerts
from backend.app.aspects.audit import audit_operation
from backend.app.aspects.authorization import requires_role
from backend.app.core.auth import CurrentUser, get_current_user
from backend.app.models.coordination_transfer import (
    CoordinationTransferActionResponse,
    CoordinationTransferResponse,
    CoordinationTransferStartRequest,
)
from backend.app.services.coordination_transfer_service import (
    CoordinationTransferService,
)

router = APIRouter()


def _transfer_notification(
    *,
    user_id: str,
    programa_id: str,
    tipo: str,
    titulo: str,
    mensagem: str,
) -> dict[str, Any]:
    return {
        "destinatario_id": user_id,
        "programa_id": programa_id,
        "tipo": tipo,
        "titulo": titulo,
        "mensagem": mensagem,
    }


def _notify_successor(result: CoordinationTransferResponse, args: Any, kwargs: Any) -> dict[str, Any]:
    return _transfer_notification(
        user_id=result.successor_uid,
        programa_id=result.programa_id,
        tipo="transferencia_coordenacao",
        titulo="Convite para coordenacao",
        mensagem="Voce recebeu um convite para assumir a coordenacao do programa.",
    )


def _notify_initiator_accept(
    result: CoordinationTransferResponse,
    args: Any,
    kwargs: Any,
) -> dict[str, Any]:
    return _transfer_notification(
        user_id=result.initiator_uid,
        programa_id=result.programa_id,
        tipo="transferencia_coordenacao",
        titulo="Transferencia aceita",
        mensagem="A transferencia de coordenacao foi aceita pelo sucessor.",
    )


def _notify_initiator_reject(
    result: CoordinationTransferResponse,
    args: Any,
    kwargs: Any,
) -> dict[str, Any]:
    return _transfer_notification(
        user_id=result.initiator_uid,
        programa_id=result.programa_id,
        tipo="transferencia_coordenacao",
        titulo="Transferencia rejeitada",
        mensagem="O convite de transferencia de coordenacao foi rejeitado.",
    )


def _notify_successor_cancel(
    result: CoordinationTransferResponse,
    args: Any,
    kwargs: Any,
) -> dict[str, Any]:
    return _transfer_notification(
        user_id=result.successor_uid,
        programa_id=result.programa_id,
        tipo="transferencia_coordenacao",
        titulo="Transferencia cancelada",
        mensagem="O convite de transferencia de coordenacao foi cancelado.",
    )



@router.post(
    "/coordination-transfers",
    status_code=status.HTTP_201_CREATED,
)
@requires_role("adm", "coordenacao")
@audit_operation
@trigger_alerts(_notify_successor)
async def start_transfer(
    body: CoordinationTransferStartRequest,
    user: CurrentUser = Depends(get_current_user),
) -> CoordinationTransferResponse:
    return await CoordinationTransferService().start_transfer(body, user)


@router.get("/coordination-transfers")
@requires_role("coordenacao", "orientador")
async def list_transfers(
    user: CurrentUser = Depends(get_current_user),
) -> list[CoordinationTransferResponse]:
    return await CoordinationTransferService().list_transfers(user)


@router.post("/coordination-transfers/{transfer_id}/accept")
@requires_role("orientador")
@audit_operation
@trigger_alerts(_notify_initiator_accept)
async def accept_transfer(
    transfer_id: str,
    user: CurrentUser = Depends(get_current_user),
) -> CoordinationTransferActionResponse:
    transfer = await CoordinationTransferService().accept_transfer(transfer_id, user)
    return CoordinationTransferActionResponse(
        message="Transferencia aceita",
        id=transfer.id,
        programa_id=transfer.programa_id,
        initiator_uid=transfer.initiator_uid,
        successor_uid=transfer.successor_uid,
        status=transfer.status,
    )


@router.post("/coordination-transfers/{transfer_id}/reject")
@requires_role("orientador")
@audit_operation
@trigger_alerts(_notify_initiator_reject)
async def reject_transfer(
    transfer_id: str,
    user: CurrentUser = Depends(get_current_user),
) -> CoordinationTransferActionResponse:
    transfer = await CoordinationTransferService().reject_transfer(transfer_id, user)
    return CoordinationTransferActionResponse(
        message="Transferencia rejeitada",
        id=transfer.id,
        programa_id=transfer.programa_id,
        initiator_uid=transfer.initiator_uid,
        successor_uid=transfer.successor_uid,
        status=transfer.status,
    )


@router.post("/coordination-transfers/{transfer_id}/cancel")
@requires_role("adm", "coordenacao")
@audit_operation
@trigger_alerts(_notify_successor_cancel)
async def cancel_transfer(
    transfer_id: str,
    user: CurrentUser = Depends(get_current_user),
) -> CoordinationTransferActionResponse:
    transfer = await CoordinationTransferService().cancel_transfer(transfer_id, user)
    return CoordinationTransferActionResponse(
        message="Transferencia cancelada",
        id=transfer.id,
        programa_id=transfer.programa_id,
        initiator_uid=transfer.initiator_uid,
        successor_uid=transfer.successor_uid,
        status=transfer.status,
    )
