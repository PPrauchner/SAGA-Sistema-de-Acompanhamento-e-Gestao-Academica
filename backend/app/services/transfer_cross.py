# backend/app/services/transfer_cross.py
from datetime import datetime
from fastapi import HTTPException, status
from backend.app.services.inference_service import InferenceService

class CrossProgramTransferService:
    def __init__(self, transfer_repo, student_repo):
        self.transfer_repo = transfer_repo
        self.student_repo = student_repo
        self.inference_service = InferenceService()

    async def create_request(self, request_data, current_user):
        student = await self.student_repo.get_by_id(request_data.student_id)
        if not student:
            raise HTTPException(status_code=404, detail="Discente nao encontrado.")

        if student.get("situacao_registrada") in ["concluido", "desligado"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Discentes concluidos ou desligados nao podem sofrer transferencia acadêmica."
            )

        if await self.transfer_repo.has_pending_request(request_data.student_id):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Ja existe uma solicitacao de transferencia pendente para este discente."
            )

        is_cross = request_data.programa_origem_id != request_data.programa_destino_id

        payload = {
            "student_id": request_data.student_id,
            "orientador_origem_id": student.get("orientador_id"),
            "orientador_destino_id": request_data.orientador_destino_id,
            "programa_origem_id": request_data.programa_origem_id,
            "programa_destino_id": request_data.programa_destino_id,
            "solicitante_id": current_user.uid,
            "status": "pendente_origem" if is_cross else "pendente_destino",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }

        return await self.transfer_repo.save(payload)

    async def approve_origin_stage(self, transfer_id: str, current_user: str):
        transfer = await self.transfer_repo.get_by_id(transfer_id)
        if not transfer or transfer.get("status") != "pendente_origem":
            raise HTTPException(status_code=400, detail="Acao invalida para o estado atual desta transferencia.")

        updates = {
            "status": "pendente_destino",
            "origem_approved_at": datetime.utcnow(),
            "origem_approved_by": current_user,
            "updated_at": datetime.utcnow()
        }
        return await self.transfer_repo.update(transfer_id, updates)

    async def approve_destination_stage(self, transfer_id: str, current_user: str):
        transfer = await self.transfer_repo.get_by_id(transfer_id)
        if not transfer or transfer.get("status") != "pendente_destino":
            raise HTTPException(status_code=400, detail="Transferencia nao esta pronta para homologacao de destino.")

        orientador_id = transfer.get("orientador_destino_id")
        student_id = transfer.get("student_id")

        active_count = await self.transfer_repo.get_active_advising_count(orientador_id)
        if active_count >= 5:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="O orientador de destino atingiu o limite maximo de 5 orientandos ativos."
            )

        student_updates = {
            "programa_id": transfer.get("programa_destino_id"),
            "orientador_id": orientador_id,
            "coorientador_id": None,
            "updated_at": datetime.utcnow()
        }
        await self.student_repo.update(student_id, student_updates)

        transfer_updates = {
            "status": "aprovada",
            "approved_at": datetime.utcnow(),
            "approved_by": current_user,
            "updated_at": datetime.utcnow()
        }
        result = await self.transfer_repo.update(transfer_id, transfer_updates)

        await self.inference_service.recalculate_student_rules(student_id)
        return result

    async def reject_transfer(self, transfer_id: str, motivo: str, current_user: str):
        updates = {
            "status": "rejeitada",
            "motivo_rejeicao": motivo,
            "rejected_by": current_user,
            "rejected_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        return await self.transfer_repo.update(transfer_id, updates)