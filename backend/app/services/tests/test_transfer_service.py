from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pytest
from fastapi import HTTPException

from backend.app.core.auth import CurrentUser
from backend.app.models.transfer import DirectTransferRequest
from backend.app.services import transfer_service as transfer_module
from backend.app.services.transfer_service import TransferService


class _FakeRepo:
    store: dict[str, dict[str, Any]] = {}
    prefix = "doc"
    counter = 0

    async def create(self, data: dict[str, Any]) -> str:
        type(self).counter += 1
        doc_id = f"{self.prefix}{type(self).counter}"
        type(self).store[doc_id] = dict(data)
        return doc_id

    async def get(self, doc_id: str) -> dict[str, Any] | None:
        data = type(self).store.get(doc_id)
        return {"id": doc_id, **data} if data else None

    async def update(self, doc_id: str, data: dict[str, Any]) -> None:
        type(self).store.setdefault(doc_id, {}).update(data)

    async def list_all(self) -> list[dict[str, Any]]:
        return [{"id": key, **value} for key, value in type(self).store.items()]


class _FakeStudentRepository(_FakeRepo):
    store: dict[str, dict[str, Any]] = {}
    prefix = "student"
    counter = 0


class _FakeAdvisorRepository(_FakeRepo):
    store: dict[str, dict[str, Any]] = {}
    prefix = "advisor"
    counter = 0

    async def check_advisor_capacity(self, advisor_id: str) -> bool:
        advisor = self.store.get(advisor_id)
        if advisor is None:
            return False
        students = await _FakeStudentRepository().list_all()
        current = sum(1 for student in students if student.get("orientador_id") == advisor_id)
        return current < advisor.get("limite_orientandos", 5)


class _FakeTransferRepository(_FakeRepo):
    store: dict[str, dict[str, Any]] = {}
    prefix = "transfer"
    counter = 0

    async def get_pending_by_student(self, student_id: str) -> dict[str, Any] | None:
        transfers = await self.list_all()
        return next(
            (
                transfer
                for transfer in transfers
                if transfer.get("student_id") == student_id
                and transfer.get("status") == "pendente"
            ),
            None,
        )


def _coord() -> CurrentUser:
    return CurrentUser(
        uid="coord1",
        role="coordenacao",
        programa_id="prog",
        email="coord@saga.test",
    )


@pytest.fixture(autouse=True)
def _setup(monkeypatch: pytest.MonkeyPatch) -> None:
    _FakeStudentRepository.store = {
        "student1": {
            "uid": "uid-student",
            "nome": "Aluno",
            "orientador_id": "advisor1",
            "coorientador_id": "advisor3",
            "programa_id": "prog",
            "situacao_registrada": "regular",
        },
    }
    _FakeAdvisorRepository.store = {
        "advisor1": {
            "uid": "uid-origin",
            "nome": "Origem",
            "programa_id": "prog",
            "limite_orientandos": 5,
        },
        "advisor2": {
            "uid": "uid-destination",
            "nome": "Destino",
            "programa_id": "prog",
            "limite_orientandos": 5,
        },
        "advisor3": {
            "uid": "uid-coadvisor",
            "nome": "Coorientador",
            "programa_id": "prog",
            "limite_orientandos": 5,
        },
    }
    _FakeTransferRepository.store = {}
    _FakeTransferRepository.counter = 0
    monkeypatch.setattr(transfer_module, "StudentRepository", _FakeStudentRepository)
    monkeypatch.setattr(transfer_module, "AdvisorRepository", _FakeAdvisorRepository)
    monkeypatch.setattr(transfer_module, "TransferRepository", _FakeTransferRepository)


async def test_direct_transfer_atualiza_orientador_e_cria_request_aprovada() -> None:
    result = await TransferService().direct_transfer(
        DirectTransferRequest(student_id="student1", orientador_destino_id="advisor2"),
        _coord(),
    )

    assert result["orientador_origem_id"] == "advisor1"
    assert result["orientador_destino_id"] == "advisor2"
    assert _FakeStudentRepository.store["student1"]["orientador_id"] == "advisor2"
    transfer = _FakeTransferRepository.store[result["id"]]
    assert transfer["status"] == "aprovada"
    assert transfer["tipo"] == "direta_coordenacao"
    assert transfer["solicitante_id"] == "coord1"


async def test_direct_transfer_bloqueia_destino_cheio() -> None:
    _FakeAdvisorRepository.store["advisor2"]["limite_orientandos"] = 1
    _FakeStudentRepository.store["student2"] = {
        "orientador_id": "advisor2",
        "programa_id": "prog",
        "situacao_registrada": "regular",
    }

    with pytest.raises(HTTPException) as exc_info:
        await TransferService().direct_transfer(
            DirectTransferRequest(student_id="student1", orientador_destino_id="advisor2"),
            _coord(),
        )

    assert exc_info.value.status_code == 400
    assert "limite" in str(exc_info.value.detail)


async def test_direct_transfer_bloqueia_status_terminal() -> None:
    _FakeStudentRepository.store["student1"]["situacao_registrada"] = "concluido"

    with pytest.raises(HTTPException) as exc_info:
        await TransferService().direct_transfer(
            DirectTransferRequest(student_id="student1", orientador_destino_id="advisor2"),
            _coord(),
        )

    assert exc_info.value.status_code == 400
    assert "status terminal" in str(exc_info.value.detail)


async def test_direct_transfer_para_coorientador_limpa_coorientador_id() -> None:
    result = await TransferService().direct_transfer(
        DirectTransferRequest(student_id="student1", orientador_destino_id="advisor3"),
        _coord(),
    )

    assert result["coorientador_limpo"] is True
    assert _FakeStudentRepository.store["student1"]["orientador_id"] == "advisor3"
    assert _FakeStudentRepository.store["student1"]["coorientador_id"] is None


async def test_direct_transfer_cancela_pendente_do_aluno() -> None:
    _FakeTransferRepository.store = {
        "transfer_old": {
            "student_id": "student1",
            "status": "pendente",
            "tipo": "solicitada_aluno",
            "solicitante_id": "uid-student",
            "created_at": datetime.now(timezone.utc),
        },
    }

    result = await TransferService().direct_transfer(
        DirectTransferRequest(student_id="student1", orientador_destino_id="advisor2"),
        _coord(),
    )

    assert result["pending_cancelled"] is True
    assert result["pending_solicitante_id"] == "uid-student"
    assert _FakeTransferRepository.store["transfer_old"]["status"] == "cancelada"
    assert _FakeTransferRepository.store["transfer_old"]["cancelled_by"] == "coord1"


async def test_direct_transfer_bloqueia_programa_diferente() -> None:
    _FakeAdvisorRepository.store["advisor2"]["programa_id"] = "outro"

    with pytest.raises(HTTPException) as exc_info:
        await TransferService().direct_transfer(
            DirectTransferRequest(student_id="student1", orientador_destino_id="advisor2"),
            _coord(),
        )

    assert exc_info.value.status_code == 400
    assert "mesmo programa" in str(exc_info.value.detail)
