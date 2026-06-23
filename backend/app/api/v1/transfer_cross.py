# backend/app/api/v1/endpoints/transfer_cross.py
from fastapi import APIRouter, Depends, status
from backend.app.core.auth import get_current_user, CurrentUser
from backend.app.models.transfer_cross import TransferRequestCreate, TransferRejectPayload
from backend.app.services.transfer_cross import CrossProgramTransferService
from backend.app.repositories.transfer_firestore import FirestoreTransferRepo
from backend.app.repositories.student_firestore import FirestoreStudentRepo
from backend.app.aspects.decorators import requires_role, audit_operation, check_deadlines, trigger_alerts

router = APIRouter(prefix="/transferencias-cross", tags=["Transferencias Cross-Program"])

def get_service():
    return CrossProgramTransferService(
        transfer_repo=FirestoreTransferRepo(), 
        student_repo=FirestoreStudentRepo()
    )

@router.post("/", status_code=status.HTTP_201_CREATED)
@requires_role("coordenacao", "orientador")
@audit_operation
@check_deadlines
@trigger_alerts
async def criar_solicitacao(payload: TransferRequestCreate, current_user: CurrentUser = Depends(get_current_user), service: CrossProgramTransferService = Depends(get_service)):
    return await service.create_request(payload, current_user)

@router.patch("/{id}/aprovar-origem")
@requires_role("coordenacao")
@audit_operation
@check_deadlines
@trigger_alerts
async def homologar_origem(id: str, current_user: CurrentUser = Depends(get_current_user), service: CrossProgramTransferService = Depends(get_service)):
    return await service.approve_origin_stage(id, current_user.uid)

@router.patch("/{id}/aprovar-destino")
@requires_role("coordenacao")
@audit_operation
@check_deadlines
@trigger_alerts
async def homologar_destino(id: str, current_user: CurrentUser = Depends(get_current_user), service: CrossProgramTransferService = Depends(get_service)):
    return await service.approve_destination_stage(id, current_user.uid)

@router.patch("/{id}/rejeitar")
@requires_role("coordenacao")
@audit_operation
@check_deadlines
@trigger_alerts
async def rejeitar_solicitacao(id: str, payload: TransferRejectPayload, current_user: CurrentUser = Depends(get_current_user), service: CrossProgramTransferService = Depends(get_service)):
    return await service.reject_transfer(id, payload.motivo, current_user.uid)