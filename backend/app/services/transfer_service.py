"""Servico de transferencia de orientandos."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException, status

from backend.app.core.auth import CurrentUser
from backend.app.models.transfer import DirectTransferRequest, TransferCreateRequest
from backend.app.repositories.advisor_repository import AdvisorRepository
from backend.app.repositories.firebase_repository import FirebaseRepository
from backend.app.repositories.student_repository import StudentRepository
from backend.app.repositories.transfer_repository import TransferRepository

_TERMINAL_STATUSES = {"concluido", "desligado"}


class TransferService:
    def __init__(self) -> None:
        self._students = StudentRepository()
        self._advisors = AdvisorRepository()
        self._transfers = TransferRepository()
        self._users = FirebaseRepository("users")

    async def _get_advisor_id_for_user(self, user: CurrentUser) -> str | None:
        advisors = await self._advisors.list_all()
        advisor = next(
            (item for item in advisors if item.get("uid") == user.uid),
            None,
        )
        return advisor["id"] if advisor else None

    async def _get_coord_uids(self, programa_id: str | None) -> list[str]:
        if not programa_id:
            return []
        users = await self._users.list_all()
        return [
            user["id"]
            for user in users
            if user.get("role") == "coordenacao"
            and user.get("programa_id") == programa_id
        ]

    async def _get_required_student(self, student_id: str) -> dict[str, Any]:
        student = await self._students.get(student_id)
        if student is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Aluno nao encontrado",
            )
        student["id"] = student_id
        return student

    async def _get_required_advisor(self, advisor_id: str, label: str) -> dict[str, Any]:
        advisor = await self._advisors.get(advisor_id)
        if advisor is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Orientador {label} nao encontrado",
            )
        advisor["id"] = advisor_id
        return advisor

    async def _validate_transfer_target(
        self,
        student: dict[str, Any],
        destination: dict[str, Any],
    ) -> None:
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

        if student.get("orientador_id") == destination["id"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Orientador destino ja e o orientador atual do aluno",
            )

        if not await self._advisors.check_advisor_capacity(destination["id"]):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Orientador destino atingiu o limite de orientandos",
            )

    async def _execute_transfer(
        self,
        student_id: str,
        destination_id: str,
        user: CurrentUser,
    ) -> dict[str, Any]:
        student = await self._get_required_student(student_id)
        destination = await self._get_required_advisor(destination_id, "destino")

        await self._validate_transfer_target(student, destination)

        if user.programa_id and user.programa_id != student.get("programa_id"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Usuario nao pode transferir aluno de outro programa",
            )

        origin_id = student.get("orientador_id")
        origin = await self._advisors.get(origin_id) if origin_id else None
        coorientador_limpo = student.get("coorientador_id") == destination_id

        update_data: dict[str, Any] = {"orientador_id": destination_id}
        if coorientador_limpo:
            update_data["coorientador_id"] = None

        await self._students.update(student_id, update_data)

        return {
            "student_id": student_id,
            "student_uid": student.get("uid"),
            "student_nome": student.get("nome"),
            "orientador_origem_id": origin_id,
            "orientador_origem_uid": origin.get("uid") if origin else None,
            "orientador_origem_nome": origin.get("nome") if origin else None,
            "orientador_destino_id": destination_id,
            "orientador_destino_uid": destination.get("uid"),
            "orientador_destino_nome": destination.get("nome"),
            "programa_id": student.get("programa_id"),
            "coorientador_limpo": coorientador_limpo,
        }

    async def direct_transfer(
        self,
        data: DirectTransferRequest,
        user: CurrentUser,
    ) -> dict[str, Any]:
        now = datetime.now(timezone.utc)
        pending = await self._transfers.get_pending_by_student(data.student_id)
        if pending is not None:
            await self._transfers.cancel(
                pending["id"],
                {
                    "cancelled_at": now,
                    "cancelado_em": now,
                    "updated_at": now,
                    "cancelled_by": user.uid,
                    "cancelado_por": user.uid,
                    "cancel_reason": "Transferencia direta realizada pela coordenacao",
                },
            )

        result = await self._execute_transfer(
            data.student_id,
            data.orientador_destino_id,
            user,
        )

        transfer_id = await self._transfers.create_request(
            {
                "student_id": data.student_id,
                "orientador_origem_id": result["orientador_origem_id"],
                "orientador_destino_id": data.orientador_destino_id,
                "status": "aprovada",
                "tipo": "direta_coordenacao",
                "solicitante_id": user.uid,
                "programa_id": result.get("programa_id"),
                "created_at": now,
                "updated_at": now,
                "approved_at": now,
                "approved_by": user.uid,
                "decidido_em": now,
                "decidido_por": user.uid,
                "observacao": data.observacao,
                "cancelled_request_id": pending["id"] if pending else None,
            },
        )

        return {
            **result,
            "id": transfer_id,
            "pending_cancelled": pending is not None,
            "pending_request_id": pending["id"] if pending else None,
            "pending_solicitante_id": pending.get("solicitante_id") if pending else None,
            "message": "Aluno transferido com sucesso",
        }

    async def create_request(
        self,
        data: TransferCreateRequest,
        user: CurrentUser,
    ) -> dict[str, Any]:
        advisor_id = await self._get_advisor_id_for_user(user)
        if advisor_id is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Orientador solicitante nao encontrado",
            )

        student = await self._get_required_student(data.student_id)
        if student.get("orientador_id") != advisor_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Orientador so pode solicitar transferencia de orientando proprio",
            )

        destination = await self._get_required_advisor(data.orientador_destino_id, "destino")
        await self._validate_transfer_target(student, destination)

        pending = await self._transfers.get_pending_by_student(data.student_id)
        if pending is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Ja existe solicitacao pendente para este aluno",
            )

        now = datetime.now(timezone.utc)
        transfer_id = await self._transfers.create_request(
            {
                "student_id": data.student_id,
                "orientador_origem_id": advisor_id,
                "orientador_destino_id": data.orientador_destino_id,
                "solicitante_id": user.uid,
                "programa_id": student.get("programa_id"),
                "status": "pendente",
                "tipo": "solicitada_orientador",
                "motivo": data.motivo,
                "created_at": now,
                "updated_at": now,
            },
        )

        return {
            "id": transfer_id,
            "student_id": data.student_id,
            "student_nome": student.get("nome"),
            "orientador_origem_id": advisor_id,
            "orientador_origem_uid": user.uid,
            "orientador_origem_nome": user.email,
            "orientador_destino_id": data.orientador_destino_id,
            "orientador_destino_uid": destination.get("uid"),
            "orientador_destino_nome": destination.get("nome"),
            "solicitante_id": user.uid,
            "programa_id": student.get("programa_id"),
            "status": "pendente",
            "motivo": data.motivo,
            "coord_uids": await self._get_coord_uids(student.get("programa_id")),
            "message": "Solicitacao de transferencia criada",
        }

    async def list_requests(self, user: CurrentUser) -> list[dict[str, Any]]:
        if user.role == "coordenacao":
            requests = await self._transfers.list_by_program(user.programa_id)
        elif user.role == "orientador":
            requests = await self._transfers.list_by_requester(user.uid)
        else:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Aluno nao pode acessar solicitacoes de transferencia",
            )

        return sorted(
            requests,
            key=lambda item: item.get("created_at") or datetime.min.replace(tzinfo=timezone.utc),
            reverse=True,
        )

    async def approve_request(
        self,
        transfer_id: str,
        user: CurrentUser,
    ) -> dict[str, Any]:
        request = await self._transfers.get(transfer_id)
        if request is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Solicitacao de transferencia nao encontrada",
            )
        if request.get("status") != "pendente":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Solicitacao precisa estar pendente para aprovacao",
            )
        if user.programa_id and user.programa_id != request.get("programa_id"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Coordenacao nao pode aprovar solicitacao de outro programa",
            )

        result = await self._execute_transfer(
            request["student_id"],
            request["orientador_destino_id"],
            user,
        )
        now = datetime.now(timezone.utc)
        await self._transfers.approve(
            transfer_id,
            {
                "updated_at": now,
                "approved_at": now,
                "approved_by": user.uid,
                "decidido_em": now,
                "decidido_por": user.uid,
            },
        )

        return {
            **result,
            "id": transfer_id,
            "solicitante_id": request.get("solicitante_id"),
            "status": "aprovada",
            "message": "Solicitacao de transferencia aprovada",
        }

    async def reject_request(
        self,
        transfer_id: str,
        motivo: str,
        user: CurrentUser,
    ) -> dict[str, Any]:
        if not motivo.strip():
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Motivo e obrigatorio para rejeitar a solicitacao",
            )

        request = await self._transfers.get(transfer_id)
        if request is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Solicitacao de transferencia nao encontrada",
            )
        if request.get("status") != "pendente":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Solicitacao precisa estar pendente para rejeicao",
            )
        if user.programa_id and user.programa_id != request.get("programa_id"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Coordenacao nao pode rejeitar solicitacao de outro programa",
            )

        now = datetime.now(timezone.utc)
        await self._transfers.reject(
            transfer_id,
            {
                "motivo": motivo,
                "updated_at": now,
                "decidido_em": now,
                "decidido_por": user.uid,
            },
        )

        return {
            **request,
            "id": transfer_id,
            "status": "rejeitada",
            "motivo": motivo,
            "message": "Solicitacao de transferencia rejeitada",
        }

    async def cancel_request(
        self,
        transfer_id: str,
        user: CurrentUser,
    ) -> dict[str, Any]:
        request = await self._transfers.get(transfer_id)
        if request is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Solicitacao de transferencia nao encontrada",
            )
        if request.get("status") != "pendente":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Solicitacao precisa estar pendente para cancelamento",
            )
        if request.get("solicitante_id") != user.uid:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Apenas o orientador solicitante pode cancelar a solicitacao",
            )

        now = datetime.now(timezone.utc)
        await self._transfers.cancel(
            transfer_id,
            {
                "updated_at": now,
                "cancelled_at": now,
                "cancelado_em": now,
                "cancelled_by": user.uid,
                "cancelado_por": user.uid,
            },
        )

        return {
            **request,
            "id": transfer_id,
            "status": "cancelada",
            "programa_id": request.get("programa_id"),
            "coord_uids": await self._get_coord_uids(request.get("programa_id")),
            "message": "Solicitacao de transferencia cancelada",
        }
