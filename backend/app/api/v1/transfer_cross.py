"""Router de transferencia cross-program.

Expoe os endpoints de dupla aprovacao sequencial:
  POST   /transfers-cross/                      — cria solicitacao
  POST   /transfers-cross/{id}/aprovar-origem   — coord origem libera
  POST   /transfers-cross/{id}/aprovar-destino  — coord destino aceita
  POST   /transfers-cross/{id}/rejeitar         — rejeita em qualquer etapa

Mover-direto cross-program nao e exposto aqui — continua bloqueado
pela logica existente em transfers.py (same-program only).
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from backend.app.aspects.alerts import trigger_alerts
from backend.app.aspects.audit import audit_operation
from backend.app.aspects.authorization import requires_role
from backend.app.aspects.deadline_validation import check_deadlines
from backend.app.core.auth import CurrentUser, get_current_user
from backend.app.models.transfer_cross import (
    TransferCrossCreateRequest,
    TransferCrossRejectRequest,
)
from backend.app.repositories.inference_repository import InferenceRepository
from backend.app.services.inference_service import InferenceService
from backend.app.services.transfer_cross import CrossProgramTransferService

_PREFIX = "/api/v1"

router = APIRouter(prefix=f"{_PREFIX}/transfers-cross", tags=["transfers-cross"])

_service = CrossProgramTransferService()


def _get_inference() -> InferenceService:
    return InferenceService(data_source=InferenceRepository())


# ------------------------------------------------------------------
# Build functions para trigger_alerts (A05 exige factory)
# ------------------------------------------------------------------

def _build_solicitacao_criada(result: dict, args: Any, kwargs: Any) -> dict | None:
    coord_uids: list[str] = result.get("coord_uids_origem", [])
    if not coord_uids:
        return None
    return [
        {
            "tipo": "transferencia_orientador",
            "titulo": "Nova solicitacao de transferencia cross-program",
            "mensagem": (
                f"Solicitacao de transferencia para o aluno "
                f"{result.get('student_nome', '')} aguarda sua aprovacao."
            ),
            "destinatario_id": uid,
            "entidade_tipo": "transfer_requests",
            "entidade_id": result.get("id", ""),
            "programa_id": result.get("programa_origem_id", ""),
        }
        for uid in coord_uids
    ]


def _build_origem_aprovada(result: dict, args: Any, kwargs: Any) -> dict | None:
    return None  # notificacao para coord destino implementada na issue de notificacoes


def _build_efetivada(result: dict, args: Any, kwargs: Any) -> dict | None:
    return None  # notificacao para aluno/orientador implementada na issue de notificacoes


def _build_rejeitada(result: dict, args: Any, kwargs: Any) -> dict | None:
    return None  # notificacao para solicitante implementada na issue de notificacoes


# ------------------------------------------------------------------
# Endpoints
# ------------------------------------------------------------------

@router.post("/", status_code=201)
@requires_role("orientador", "coordenacao")
@audit_operation
@check_deadlines
@trigger_alerts(_build_solicitacao_criada)
async def criar_solicitacao(
    data: TransferCrossCreateRequest,
    current_user: CurrentUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Cria solicitacao de transferencia cross-program.

    Join Point: Before — autorização e auditoria antes de persistir.
    Se origem == destino, colapsa para fluxo same-program (1 passo).
    """
    return await _service.create_request(
        student_id=data.student_id,
        orientador_destino_id=data.orientador_destino_id,
        programa_destino_id=data.programa_destino_id,
        motivo=data.motivo,
        user=current_user,
    )


@router.post("/{transfer_id}/aprovar-origem", status_code=200)
@requires_role("coordenacao")
@audit_operation
@check_deadlines
@trigger_alerts(_build_origem_aprovada)
async def aprovar_origem(
    transfer_id: str,
    current_user: CurrentUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Coordenacao de ORIGEM libera: pendente_origem → pendente_destino.

    Join Point: Before — restringe a coordenacao do programa de origem.
    """
    return await _service.approve_origin(transfer_id, current_user)


@router.post("/{transfer_id}/aprovar-destino", status_code=200)
@requires_role("coordenacao")
@audit_operation
@check_deadlines
@trigger_alerts(_build_efetivada)
async def aprovar_destino(
    transfer_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    inference_svc: InferenceService = Depends(_get_inference),
) -> dict[str, Any]:
    """Coordenacao de DESTINO aceita: valida capacidade, migra programa_id, roda RL02.

    Join Point: After — InferenceService executado apos persistencia.
    """
    return await _service.approve_destination(transfer_id, current_user, inference_svc)


@router.post("/{transfer_id}/rejeitar", status_code=200)
@requires_role("coordenacao")
@audit_operation
@check_deadlines
@trigger_alerts(_build_rejeitada)
async def rejeitar(
    transfer_id: str,
    data: TransferCrossRejectRequest,
    current_user: CurrentUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Rejeita em qualquer etapa com motivo obrigatorio."""
    return await _service.reject_request(transfer_id, data.motivo, current_user)