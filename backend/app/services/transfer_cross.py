"""Servico de transferencia cross-program (dupla aprovacao sequencial).

Estende o fluxo same-program existente para suportar transferencias entre
programas distintos, exigindo aprovacao da coordenacao de origem e depois
da coordenacao de destino antes de efetivar a migracao.

Mover-direto cross-program e bloqueado — continua restrito a same-program.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException, status

from backend.app.core.auth import CurrentUser
from backend.app.repositories.advisor_repository import AdvisorRepository
from backend.app.repositories.firebase_repository import FirebaseRepository
from backend.app.repositories.student_repository import StudentRepository
from backend.app.repositories.transfer_repository import TransferRepository

_TERMINAL_STATUSES = {"concluido", "desligado"}
_CROSS_PENDING_STATUSES = {"pendente_origem", "pendente_destino"}


class CrossProgramTransferService:
    """Orquestra o fluxo de dupla aprovacao para transferencias cross-program.

    Join Points cobertos:
    - create_request: cria solicitacao; se cross-program, inicia em pendente_origem.
    - approve_origin: coordenacao de origem libera → pendente_destino.
    - approve_destination: coordenacao de destino aceita → efetiva migracao + inferencia.
    - reject_request: rejeicao em qualquer etapa com motivo obrigatorio.
    """

    def __init__(self) -> None:
        self._students = StudentRepository()
        self._advisors = AdvisorRepository()
        self._transfers = TransferRepository()
        self._users = FirebaseRepository("users")

    # ------------------------------------------------------------------
    # Helpers internos
    # ------------------------------------------------------------------

    async def _get_required_student(self, student_id: str) -> dict[str, Any]:
        student = await self._students.get(student_id)
        if student is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Aluno nao encontrado",
            )
        student["id"] = student_id
        return student

    async def _get_required_transfer(self, transfer_id: str) -> dict[str, Any]:
        request = await self._transfers.get(transfer_id)
        if request is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Solicitacao de transferencia nao encontrada",
            )
        return request

    async def _get_required_advisor(self, advisor_id: str, label: str) -> dict[str, Any]:
        advisor = await self._advisors.get(advisor_id)
        if advisor is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Orientador {label} nao encontrado",
            )
        advisor["id"] = advisor_id
        return advisor

    def _assert_status(self, request: dict[str, Any], expected: str) -> None:
        if request.get("status") != expected:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Solicitacao precisa estar '{expected}' para esta acao",
            )

    async def _has_cross_pending(self, student_id: str) -> bool:
        """Verifica se existe solicitacao cross-program pendente para o aluno."""
        all_transfers = await self._transfers.list_all()
        return any(
            t.get("student_id") == student_id
            and t.get("status") in _CROSS_PENDING_STATUSES
            for t in all_transfers
        )

    # ------------------------------------------------------------------
    # Casos de uso
    # ------------------------------------------------------------------

    async def create_request(
        self,
        student_id: str,
        orientador_destino_id: str,
        programa_destino_id: str,
        motivo: str,
        user: CurrentUser,
    ) -> dict[str, Any]:
        """Cria solicitacao cross-program.

        Se origem == destino (same-program), colapsa para status 'pendente' (1 passo).
        Se cross-program, cria em 'pendente_origem' (2 passos).
        """
        student = await self._get_required_student(student_id)

        if student.get("situacao_registrada") in _TERMINAL_STATUSES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Aluno em status terminal nao pode ser transferido",
            )

        pending = await self._transfers.get_pending_by_student(student_id)
        has_cross_pending = await self._has_cross_pending(student_id)
        if pending is not None or has_cross_pending:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Ja existe solicitacao pendente para este aluno",
            )

        destination = await self._get_required_advisor(orientador_destino_id, "destino")

        if student.get("orientador_id") == orientador_destino_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Orientador destino ja e o orientador atual do aluno",
            )

        is_cross = student.get("programa_id") != programa_destino_id

        if not is_cross:
            if not await self._advisors.check_advisor_capacity(orientador_destino_id):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Orientador destino atingiu o limite de orientandos",
                )

        now = datetime.now(timezone.utc)
        transfer_id = await self._transfers.create_request(
            {
                "student_id": student_id,
                "orientador_origem_id": student.get("orientador_id"),
                "orientador_destino_id": orientador_destino_id,
                "programa_origem_id": student.get("programa_id"),
                "programa_destino_id": programa_destino_id,
                "solicitante_id": user.uid,
                "programa_id": student.get("programa_id"),
                "status": "pendente_origem" if is_cross else "pendente",
                "tipo": "solicitada_orientador",
                "motivo": motivo,
                "created_at": now,
                "updated_at": now,
            }
        )

        return {
            "id": transfer_id,
            "student_id": student_id,
            "student_nome": student.get("nome"),
            "orientador_destino_id": orientador_destino_id,
            "orientador_destino_nome": destination.get("nome"),
            "programa_origem_id": student.get("programa_id"),
            "programa_destino_id": programa_destino_id,
            "status": "pendente_origem" if is_cross else "pendente",
            "tipo": "cross_program" if is_cross else "same_program",
            "message": "Solicitacao de transferencia cross-program criada",
        }

    async def approve_origin(
        self,
        transfer_id: str,
        user: CurrentUser,
    ) -> dict[str, Any]:
        """Coordenacao de ORIGEM aprova: pendente_origem → pendente_destino."""
        request = await self._get_required_transfer(transfer_id)
        self._assert_status(request, "pendente_origem")

        if (
            user.programa_id
            and user.programa_id != request.get("programa_origem_id")
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Apenas coordenacao de origem pode aprovar esta etapa",
            )

        now = datetime.now(timezone.utc)
        await self._transfers.update_status(
            transfer_id,
            {
                "status": "pendente_destino",
                "origem_approved_at": now,
                "origem_approved_by": user.uid,
                "updated_at": now,
            },
        )

        return {
            **request,
            "id": transfer_id,
            "status": "pendente_destino",
            "message": "Origem aprovada — aguardando coordenacao de destino",
        }

    async def approve_destination(
        self,
        transfer_id: str,
        user: CurrentUser,
        inference_service: Any,
    ) -> dict[str, Any]:
        """Coordenacao de DESTINO aprova: valida capacidade, migra programa_id, roda RL02."""
        request = await self._get_required_transfer(transfer_id)
        self._assert_status(request, "pendente_destino")

        if (
            user.programa_id
            and user.programa_id != request.get("programa_destino_id")
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Apenas coordenacao de destino pode aprovar esta etapa",
            )

        orientador_destino_id = request["orientador_destino_id"]
        student_id = request["student_id"]

        if not await self._advisors.check_advisor_capacity(orientador_destino_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Orientador destino atingiu o limite de orientandos",
            )

        student = await self._get_required_student(student_id)
        destination = await self._get_required_advisor(orientador_destino_id, "destino")

        programa_destino_id = request.get("programa_destino_id")
        coorientador_limpo = student.get("coorientador_id") == orientador_destino_id

        update_data: dict[str, Any] = {
            "orientador_id": orientador_destino_id,
            "programa_id": programa_destino_id,
        }
        if coorientador_limpo:
            update_data["coorientador_id"] = None

        await self._students.update(student_id, update_data)

        now = datetime.now(timezone.utc)
        await self._transfers.approve(
            transfer_id,
            {
                "updated_at": now,
                "approved_at": now,
                "approved_by": user.uid,
            },
        )

        await inference_service.evaluate_student(student_id)

        return {
            "id": transfer_id,
            "student_id": student_id,
            "student_nome": student.get("nome"),
            "orientador_destino_id": orientador_destino_id,
            "orientador_destino_nome": destination.get("nome"),
            "programa_destino_id": programa_destino_id,
            "coorientador_limpo": coorientador_limpo,
            "status": "aprovada",
            "message": "Transferencia cross-program efetivada com sucesso",
        }

    async def reject_request(
        self,
        transfer_id: str,
        motivo: str,
        user: CurrentUser,
    ) -> dict[str, Any]:
        """Rejeicao em qualquer etapa (pendente_origem ou pendente_destino)."""
        if not motivo.strip():
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Motivo e obrigatorio para rejeitar a solicitacao",
            )

        request = await self._get_required_transfer(transfer_id)

        if request.get("status") not in _CROSS_PENDING_STATUSES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Solicitacao nao esta em etapa que permita rejeicao",
            )

        programa_origem = request.get("programa_origem_id")
        programa_destino = request.get("programa_destino_id")
        if user.programa_id and user.programa_id not in {programa_origem, programa_destino}:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Coordenacao nao tem permissao para rejeitar esta solicitacao",
            )

        now = datetime.now(timezone.utc)
        await self._transfers.reject(
            transfer_id,
            {
                "motivo": motivo,
                "updated_at": now,
                "rejected_at": now,
                "rejected_by": user.uid,
            },
        )

        return {
            **request,
            "id": transfer_id,
            "status": "rejeitada",
            "motivo": motivo,
            "message": "Solicitacao de transferencia cross-program rejeitada",
        }