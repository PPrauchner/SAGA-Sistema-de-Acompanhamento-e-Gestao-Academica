from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pytest
from fastapi import HTTPException

from backend.app.core.auth import CurrentUser
from backend.app.models.coordination_transfer import CoordinationTransferStartRequest
from backend.app.services.coordination_transfer_service import CoordinationTransferService


class _FakeRepo:
    def __init__(self, initial: dict[str, dict[str, Any]] | None = None) -> None:
        self.store = initial or {}
        self.created = 0

    async def get(self, doc_id: str) -> dict[str, Any] | None:
        item = self.store.get(doc_id)
        if item is None:
            return None
        return {**item, "id": doc_id}

    async def set(self, doc_id: str, data: dict[str, Any]) -> None:
        self.store[doc_id] = dict(data)

    async def create_transfer(self, data: dict[str, Any]) -> str:
        self.created += 1
        doc_id = f"tr{self.created}"
        self.store[doc_id] = dict(data)
        return doc_id

    async def get_transfer(self, transfer_id: str) -> dict[str, Any] | None:
        return await self.get(transfer_id)

    async def get_pending_by_program(self, programa_id: str) -> dict[str, Any] | None:
        for doc_id, item in self.store.items():
            if item.get("programa_id") == programa_id and item.get("status") == "pendente":
                return {**item, "id": doc_id}
        return None

    async def list_by_program(self, programa_id: str) -> list[dict[str, Any]]:
        return [
            {**item, "id": doc_id}
            for doc_id, item in self.store.items()
            if item.get("programa_id") == programa_id
        ]

    async def list_pending_for_successor(self, successor_uid: str) -> list[dict[str, Any]]:
        return [
            {**item, "id": doc_id}
            for doc_id, item in self.store.items()
            if item.get("successor_uid") == successor_uid and item.get("status") == "pendente"
        ]

    async def update(self, doc_id: str, data: dict[str, Any]) -> bool:
        self.store.setdefault(doc_id, {}).update(data)
        return True

    async def accept(self, transfer_id: str, data: dict[str, Any]) -> bool:
        return await self.update(transfer_id, data)

    async def reject(self, transfer_id: str, data: dict[str, Any]) -> bool:
        return await self.update(transfer_id, data)

    async def cancel(self, transfer_id: str, data: dict[str, Any]) -> bool:
        return await self.update(transfer_id, data)

    async def query(
        self,
        filters: list[tuple[str, str, Any]] | None = None,
        order_by: str | None = None,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        results = []
        for doc_id, item in self.store.items():
            include = True
            for field, op, value in filters or []:
                if op != "==" or item.get(field) != value:
                    include = False
                    break
            if include:
                results.append({**item, "id": doc_id})
        return results[:limit] if limit else results


class _FakeAuth:
    def __init__(self) -> None:
        self.claims: dict[str, dict[str, Any]] = {}
        self.revoked: list[str] = []

    def set_custom_user_claims(self, uid: str, claims: dict[str, Any]) -> None:
        self.claims[uid] = claims

    def revoke_refresh_tokens(self, uid: str) -> None:
        self.revoked.append(uid)


def _coord(uid: str = "coord") -> CurrentUser:
    return CurrentUser(uid=uid, role="coordenacao", programa_id="prog1", email="c@x.com")


def _advisor(uid: str = "adv") -> CurrentUser:
    return CurrentUser(uid=uid, role="orientador", programa_id="prog1", email="a@x.com")


def _transfer(status: str = "pendente") -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    return {
        "programa_id": "prog1",
        "initiator_uid": "coord",
        "successor_uid": "adv",
        "status": status,
        "created_at": now,
        "updated_at": now,
        "decided_at": None,
        "cancelled_at": None,
        "rejected_at": None,
    }


def _service() -> tuple[CoordinationTransferService, _FakeRepo, _FakeRepo, _FakeRepo, _FakeAuth]:
    transfers = _FakeRepo()
    users = _FakeRepo(
        {
            "coord": {
                "uid": "coord",
                "email": "coord@x.com",
                "nome": "Coord",
                "role": "coordenacao",
                "programa_id": "prog1",
            },
            "adv": {
                "uid": "adv",
                "email": "adv@x.com",
                "nome": "Adv",
                "role": "orientador",
                "programa_id": "prog1",
                "advisor_id": "advisor-adv",
            },
        }
    )
    advisors = _FakeRepo(
        {
            "advisor-adv": {
                "uid": "adv",
                "nome": "Adv",
                "email": "adv@x.com",
                "programa_id": "prog1",
                "limite_orientandos": 5,
            }
        }
    )
    auth = _FakeAuth()
    service = CoordinationTransferService(transfers, users, advisors, auth)
    return service, transfers, users, advisors, auth


async def test_coordenacao_inicia_transferencia_para_orientador_mesmo_programa() -> None:
    service, transfers, _, _, _ = _service()

    resp = await service.start_transfer(
        CoordinationTransferStartRequest(successor_uid="adv"),
        _coord(),
    )

    assert resp.status == "pendente"
    assert transfers.store[resp.id]["successor_uid"] == "adv"


async def test_sucessor_que_nao_e_orientador_e_bloqueado() -> None:
    service, _, users, _, _ = _service()
    users.store["adv"]["role"] = "aluno"

    with pytest.raises(HTTPException) as exc:
        await service.start_transfer(
            CoordinationTransferStartRequest(successor_uid="adv"),
            _coord(),
        )

    assert exc.value.status_code == 400


async def test_sucessor_de_outro_programa_e_bloqueado() -> None:
    service, _, users, _, _ = _service()
    users.store["adv"]["programa_id"] = "prog2"

    with pytest.raises(HTTPException) as exc:
        await service.start_transfer(
            CoordinationTransferStartRequest(successor_uid="adv"),
            _coord(),
        )

    assert exc.value.status_code == 400


async def test_segunda_pendente_no_mesmo_programa_retorna_409() -> None:
    service, transfers, _, _, _ = _service()
    transfers.store["tr1"] = _transfer()

    with pytest.raises(HTTPException) as exc:
        await service.start_transfer(
            CoordinationTransferStartRequest(successor_uid="adv"),
            _coord(),
        )

    assert exc.value.status_code == 409


async def test_aceite_troca_claims_roles_cria_advisor_e_revoga_tokens() -> None:
    service, transfers, users, advisors, auth = _service()
    transfers.store["tr1"] = _transfer()

    resp = await service.accept_transfer("tr1", _advisor())

    assert resp.status == "aceita"
    assert auth.claims["adv"] == {"role": "coordenacao", "programa_id": "prog1"}
    assert auth.claims["coord"] == {"role": "orientador", "programa_id": "prog1"}
    assert users.store["adv"]["role"] == "coordenacao"
    assert users.store["coord"]["role"] == "orientador"
    assert users.store["coord"]["advisor_id"] == "coord"
    assert advisors.store["coord"]["limite_orientandos"] == 5
    assert advisors.store["advisor-adv"]["uid"] == "adv"
    assert set(auth.revoked) == {"adv", "coord"}


async def test_aceite_bloqueia_programa_com_outra_coordenacao_ativa() -> None:
    service, transfers, users, _, auth = _service()
    transfers.store["tr1"] = _transfer()
    users.store["coord2"] = {
        "uid": "coord2",
        "email": "coord2@x.com",
        "nome": "Coord 2",
        "role": "coordenacao",
        "programa_id": "prog1",
    }

    with pytest.raises(HTTPException) as exc:
        await service.accept_transfer("tr1", _advisor())

    assert exc.value.status_code == 409
    assert users.store["adv"]["role"] == "orientador"
    assert auth.claims == {}


async def test_sucessor_mantem_documento_advisor_apos_virar_coordenacao() -> None:
    service, transfers, _, advisors, _ = _service()
    transfers.store["tr1"] = _transfer()
    advisors.store["advisor-adv"]["orientandos_ativos"] = 3

    await service.accept_transfer("tr1", _advisor())

    assert advisors.store["advisor-adv"]["uid"] == "adv"
    assert advisors.store["advisor-adv"]["orientandos_ativos"] == 3


async def test_rejeicao_nao_altera_papeis() -> None:
    service, transfers, users, _, auth = _service()
    transfers.store["tr1"] = _transfer()

    resp = await service.reject_transfer("tr1", _advisor())

    assert resp.status == "rejeitada"
    assert users.store["adv"]["role"] == "orientador"
    assert users.store["coord"]["role"] == "coordenacao"
    assert auth.claims == {}


async def test_iniciador_cancela_enquanto_pendente() -> None:
    service, transfers, users, _, auth = _service()
    transfers.store["tr1"] = _transfer()

    resp = await service.cancel_transfer("tr1", _coord())

    assert resp.status == "cancelada"
    assert transfers.store["tr1"]["cancelled_by"] == "coord"
    assert users.store["adv"]["role"] == "orientador"
    assert auth.claims == {}


async def test_outro_usuario_nao_cancela() -> None:
    service, transfers, _, _, _ = _service()
    transfers.store["tr1"] = _transfer()

    with pytest.raises(HTTPException) as exc:
        await service.cancel_transfer("tr1", _coord("outro"))

    assert exc.value.status_code == 403
