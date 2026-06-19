"""Servico de transferencia de orientandos."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException, status

from backend.app.core.auth import CurrentUser
from backend.app.models.transfer import DirectTransferRequest
from backend.app.repositories.advisor_repository import AdvisorRepository
from backend.app.repositories.student_repository import StudentRepository
from backend.app.repositories.transfer_repository import TransferRepository

_TERMINAL_STATUSES = {"concluido", "desligado"}


class TransferService:
    def __init__(self) -> None:
        self._students = StudentRepository()
        self._advisors = AdvisorRepository()
        self._transfers = TransferRepository()

    async def direct_transfer(
        self,
        data: DirectTransferRequest,
        user: CurrentUser,
    ) -> dict[str, Any]:
        student = await self._students.get(data.student_id)
        if student is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Aluno nao encontrado",
            )

        destination = await self._advisors.get(data.orientador_destino_id)
        if destination is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Orientador destino nao encontrado",
            )

        if student.get("situacao_registrada") in _TERMINAL_STATUSES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Aluno em status terminal nao pode ser transferido",
            )

        if student.get("programa_id") != destination.get("programa_id"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Orientador destino deve pertencer ao mesmo programa do aluno",
            )

        if user.programa_id and user.programa_id != student.get("programa_id"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Coordenacao nao pode transferir aluno de outro programa",
            )

        origin_id = student.get("orientador_id")
        if origin_id == data.orientador_destino_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Orientador destino ja e o orientador atual do aluno",
            )

        if not await self._advisors.check_advisor_capacity(data.orientador_destino_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Orientador destino atingiu o limite de orientandos",
            )

        now = datetime.now(timezone.utc)
        pending = await self._transfers.get_pending_by_student(data.student_id)
        if pending is not None:
            await self._transfers.update(
                pending["id"],
                {
                    "status": "cancelada",
                    "cancelled_at": now,
                    "updated_at": now,
                    "cancelled_by": user.uid,
                    "cancel_reason": "Transferencia direta realizada pela coordenacao",
                },
            )

        coorientador_limpo = student.get("coorientador_id") == data.orientador_destino_id
        update_data: dict[str, Any] = {
            "orientador_id": data.orientador_destino_id,
        }
        if coorientador_limpo:
            update_data["coorientador_id"] = None

        await self._students.update(data.student_id, update_data)

        transfer_id = await self._transfers.create(
            {
                "student_id": data.student_id,
                "orientador_origem_id": origin_id,
                "orientador_destino_id": data.orientador_destino_id,
                "status": "aprovada",
                "tipo": "direta_coordenacao",
                "solicitante_id": user.uid,
                "programa_id": student.get("programa_id"),
                "created_at": now,
                "updated_at": now,
                "approved_at": now,
                "approved_by": user.uid,
                "observacao": data.observacao,
                "cancelled_request_id": pending["id"] if pending else None,
            },
        )

        origin = await self._advisors.get(origin_id) if origin_id else None

        return {
            "id": transfer_id,
            "student_id": data.student_id,
            "student_uid": student.get("uid"),
            "student_nome": student.get("nome"),
            "orientador_origem_id": origin_id,
            "orientador_origem_uid": origin.get("uid") if origin else None,
            "orientador_origem_nome": origin.get("nome") if origin else None,
            "orientador_destino_id": data.orientador_destino_id,
            "orientador_destino_uid": destination.get("uid"),
            "orientador_destino_nome": destination.get("nome"),
            "programa_id": student.get("programa_id"),
            "coorientador_limpo": coorientador_limpo,
            "pending_cancelled": pending is not None,
            "pending_request_id": pending["id"] if pending else None,
            "pending_solicitante_id": pending.get("solicitante_id") if pending else None,
            "message": "Aluno transferido com sucesso",
        }
