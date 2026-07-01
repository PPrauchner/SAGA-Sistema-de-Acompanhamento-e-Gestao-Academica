"""Servico do fluxo de transferencia de coordenacao."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException, status

from backend.app.core.auth import CurrentUser
from backend.app.core.firebase import get_auth_client
from backend.app.models.coordination_transfer import (
    CoordinationTransferResponse,
    CoordinationTransferStartRequest,
)
from backend.app.repositories.advisor_repository import AdvisorRepository
from backend.app.repositories.coordination_transfer_repository import (
    CoordinationTransferRepository,
)
from backend.app.repositories.firebase_repository import FirebaseRepository

_PENDING = "pendente"
_ACCEPTED = "aceita"


class CoordinationTransferService:
    def __init__(
        self,
        transfer_repo: CoordinationTransferRepository | None = None,
        user_repo: FirebaseRepository | None = None,
        advisor_repo: AdvisorRepository | None = None,
        auth_client: Any | None = None,
    ) -> None:
        self._transfers = transfer_repo or CoordinationTransferRepository()
        self._users = user_repo or FirebaseRepository("users")
        self._advisors = advisor_repo or AdvisorRepository()
        self._auth = auth_client if auth_client is not None else get_auth_client()

    async def start_transfer(
        self,
        data: CoordinationTransferStartRequest,
        current_user: CurrentUser,
    ) -> CoordinationTransferResponse:
        successor = await self._get_user(data.successor_uid, "Sucessor nao encontrado")

        if successor.get("role") != "orientador":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Sucessor precisa ser orientador",
            )
        if successor.get("programa_id") != current_user.programa_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Sucessor precisa pertencer ao mesmo programa",
            )

        pending = await self._transfers.get_pending_by_program(current_user.programa_id)
        if pending is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Ja existe transferencia pendente para este programa",
            )

        now = datetime.now(timezone.utc)
        transfer_id = await self._transfers.create_transfer(
            {
                "programa_id": current_user.programa_id,
                "initiator_uid": current_user.uid,
                "successor_uid": data.successor_uid,
                "status": _PENDING,
                "created_at": now,
                "updated_at": now,
                "decided_at": None,
                "cancelled_at": None,
                "rejected_at": None,
            }
        )
        transfer = await self._transfers.get_transfer(transfer_id)
        return self._to_response(transfer or {"id": transfer_id})

    async def force_transfer(
        self,
        data: CoordinationTransferStartRequest,
        current_user: CurrentUser,
    ) -> CoordinationTransferResponse:
        successor = await self._get_user(data.successor_uid, "Sucessor nao encontrado")

        if successor.get("role") != "orientador":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Sucessor precisa ser orientador",
            )
            
        programa_id = successor.get("programa_id")
        if not programa_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Sucessor nao pertence a um programa",
            )

        if current_user.role == "coordenacao" and current_user.programa_id != programa_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Apenas administradores podem transferir coordenacao de outros programas",
            )

        coordinations = await self._users.query(
            filters=[
                ("programa_id", "==", programa_id),
                ("role", "==", "coordenacao"),
            ]
        )
        if not coordinations:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Nenhuma coordenacao atual encontrada para o programa",
            )
        initiator = coordinations[0]
        initiator_uid = initiator.get("uid", initiator.get("id"))
        successor_uid = successor.get("uid", successor.get("id"))

        if initiator_uid == successor_uid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="O sucessor ja e o coordenador atual",
            )

        successor_claims = {
            "role": "coordenacao",
            "programa_id": programa_id,
        }
        initiator_claims = {
            "role": "orientador",
            "programa_id": programa_id,
        }

        await asyncio.to_thread(
            self._auth.set_custom_user_claims,
            successor_uid,
            successor_claims,
        )
        await asyncio.to_thread(
            self._auth.set_custom_user_claims,
            initiator_uid,
            initiator_claims,
        )

        advisor_id = await self._ensure_initiator_advisor(initiator)

        now = datetime.now(timezone.utc)
        await self._users.update(
            successor_uid,
            {"role": "coordenacao", "atualizado_em": now},
        )
        initiator_update = {
            "role": "orientador",
            "atualizado_em": now,
        }
        if advisor_id:
            initiator_update["advisor_id"] = advisor_id
        await self._users.update(initiator_uid, initiator_update)

        await asyncio.to_thread(
            self._auth.revoke_refresh_tokens,
            successor_uid,
        )
        await asyncio.to_thread(
            self._auth.revoke_refresh_tokens,
            initiator_uid,
        )

        transfer_id = await self._transfers.create_transfer(
            {
                "programa_id": programa_id,
                "initiator_uid": initiator_uid,
                "successor_uid": successor_uid,
                "status": "concluido",
                "created_at": now,
                "updated_at": now,
                "decided_at": now,
                "accepted_at": now,
                "cancelled_at": None,
                "rejected_at": None,
                "forced_by": current_user.uid,
            }
        )
        
        transfer = await self._transfers.get_transfer(transfer_id)
        return self._to_response(transfer or {"id": transfer_id})


    async def accept_transfer(
        self,
        transfer_id: str,
        current_user: CurrentUser,
    ) -> CoordinationTransferResponse:
        transfer = await self._get_pending_transfer(transfer_id)
        if transfer["successor_uid"] != current_user.uid:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Apenas o sucessor pode aceitar a transferencia",
            )

        initiator = await self._get_user(
            transfer["initiator_uid"],
            "Coordenacao iniciadora nao encontrada",
        )
        successor = await self._get_user(
            transfer["successor_uid"],
            "Sucessor nao encontrado",
        )

        if successor.get("role") != "orientador":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Sucessor precisa continuar como orientador",
            )
        if successor.get("programa_id") != transfer["programa_id"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Sucessor precisa continuar no mesmo programa",
            )
        if initiator.get("programa_id") != transfer["programa_id"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Iniciador nao pertence mais ao programa da transferencia",
            )

        await self._ensure_single_coordination(transfer["programa_id"], initiator["uid"])

        successor_claims = {
            "role": "coordenacao",
            "programa_id": transfer["programa_id"],
        }
        initiator_claims = {
            "role": "orientador",
            "programa_id": transfer["programa_id"],
        }

        await asyncio.to_thread(
            self._auth.set_custom_user_claims,
            transfer["successor_uid"],
            successor_claims,
        )
        await asyncio.to_thread(
            self._auth.set_custom_user_claims,
            transfer["initiator_uid"],
            initiator_claims,
        )

        advisor_id = await self._ensure_initiator_advisor(initiator)

        await self._users.update(
            transfer["successor_uid"],
            {"role": "coordenacao", "atualizado_em": datetime.now(timezone.utc)},
        )
        initiator_update = {
            "role": "orientador",
            "atualizado_em": datetime.now(timezone.utc),
        }
        if advisor_id:
            initiator_update["advisor_id"] = advisor_id
        await self._users.update(transfer["initiator_uid"], initiator_update)

        await asyncio.to_thread(
            self._auth.revoke_refresh_tokens,
            transfer["successor_uid"],
        )
        await asyncio.to_thread(
            self._auth.revoke_refresh_tokens,
            transfer["initiator_uid"],
        )

        now = datetime.now(timezone.utc)
        await self._transfers.accept(
            transfer_id,
            {
                "status": _ACCEPTED,
                "updated_at": now,
                "decided_at": now,
                "accepted_at": now,
            },
        )
        updated = await self._transfers.get_transfer(transfer_id)
        return self._to_response(updated or {**transfer, "status": _ACCEPTED, "updated_at": now})

    async def reject_transfer(
        self,
        transfer_id: str,
        current_user: CurrentUser,
    ) -> CoordinationTransferResponse:
        transfer = await self._get_pending_transfer(transfer_id)
        if transfer["successor_uid"] != current_user.uid:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Apenas o sucessor pode rejeitar a transferencia",
            )

        now = datetime.now(timezone.utc)
        await self._transfers.reject(
            transfer_id,
            {
                "status": "rejeitada",
                "updated_at": now,
                "decided_at": now,
                "rejected_at": now,
                "rejected_by": current_user.uid,
            },
        )
        updated = await self._transfers.get_transfer(transfer_id)
        return self._to_response(updated or {**transfer, "status": "rejeitada", "updated_at": now})

    async def cancel_transfer(
        self,
        transfer_id: str,
        current_user: CurrentUser,
    ) -> CoordinationTransferResponse:
        transfer = await self._get_pending_transfer(transfer_id)
        if transfer["initiator_uid"] != current_user.uid:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Apenas o iniciador pode cancelar a transferencia",
            )

        now = datetime.now(timezone.utc)
        await self._transfers.cancel(
            transfer_id,
            {
                "status": "cancelada",
                "updated_at": now,
                "cancelled_at": now,
                "cancelled_by": current_user.uid,
            },
        )
        updated = await self._transfers.get_transfer(transfer_id)
        return self._to_response(updated or {**transfer, "status": "cancelada", "updated_at": now})

    async def list_transfers(
        self,
        current_user: CurrentUser,
    ) -> list[CoordinationTransferResponse]:
        if current_user.role == "coordenacao":
            transfers = await self._transfers.list_by_program(current_user.programa_id)
        elif current_user.role == "orientador":
            transfers = await self._transfers.list_pending_for_successor(current_user.uid)
        else:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Papel insuficiente para listar transferencias",
            )
        return [self._to_response(item) for item in transfers]

    async def _get_pending_transfer(self, transfer_id: str) -> dict[str, Any]:
        transfer = await self._transfers.get_transfer(transfer_id)
        if transfer is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Transferencia nao encontrada",
            )
        if transfer.get("status") != _PENDING:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Transferencia precisa estar pendente",
            )
        return transfer

    async def _get_user(self, uid: str, not_found_detail: str) -> dict[str, Any]:
        user = await self._users.get(uid)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=not_found_detail,
            )
        user.setdefault("uid", uid)
        return user

    async def _ensure_single_coordination(
        self,
        programa_id: str,
        initiator_uid: str,
    ) -> None:
        coordinations = await self._users.query(
            filters=[
                ("programa_id", "==", programa_id),
                ("role", "==", "coordenacao"),
            ]
        )
        invalid = [
            user for user in coordinations if user.get("uid", user.get("id")) != initiator_uid
        ]
        if invalid:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Programa possui outra coordenacao ativa",
            )

    async def _ensure_initiator_advisor(self, initiator: dict[str, Any]) -> str | None:
        existing_id = initiator.get("advisor_id")
        if existing_id and await self._advisors.get(existing_id):
            return existing_id

        advisors = await self._advisors.query(filters=[("uid", "==", initiator["uid"])], limit=1)
        if advisors:
            return advisors[0]["id"]

        advisor_id = existing_id or initiator["uid"]
        await self._advisors.set(
            advisor_id,
            {
                "uid": initiator["uid"],
                "nome": initiator.get("nome", initiator.get("email", initiator["uid"])),
                "email": initiator.get("email", ""),
                "departamento": initiator.get("departamento", ""),
                "programa_id": initiator["programa_id"],
                "lattes": initiator.get("lattes"),
                "limite_orientandos": 5,
            },
        )
        return advisor_id

    @staticmethod
    def _to_response(data: dict[str, Any]) -> CoordinationTransferResponse:
        return CoordinationTransferResponse(
            id=data["id"],
            programa_id=data["programa_id"],
            initiator_uid=data["initiator_uid"],
            successor_uid=data["successor_uid"],
            status=data["status"],
            created_at=data["created_at"],
            updated_at=data["updated_at"],
            decided_at=data.get("decided_at"),
            cancelled_at=data.get("cancelled_at"),
            rejected_at=data.get("rejected_at"),
            accepted_at=data.get("accepted_at"),
            rejected_by=data.get("rejected_by"),
            cancelled_by=data.get("cancelled_by"),
        )
