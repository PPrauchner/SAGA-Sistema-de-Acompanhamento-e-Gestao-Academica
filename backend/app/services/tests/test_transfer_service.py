from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pytest
from fastapi import HTTPException

from backend.app.core.auth import CurrentUser
from backend.app.models.transfer import DirectTransferRequest, TransferCreateRequest
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
        current = sum(
            1
            for student in students
            if student.get("orientador_id") == advisor_id
            and student.get("situacao_registrada") not in {"concluido", "desligado"}
        )
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

    async def create_request(self, data: dict[str, Any]) -> str:
        return await self.create(data)

    async def list_by_program(self, programa_id: str) -> list[dict[str, Any]]:
        return [
            request
            for request in await self.list_all()
            if request.get("programa_id") == programa_id
        ]

    async def list_by_requester(self, solicitante_id: str) -> list[dict[str, Any]]:
        return [
            request
            for request in await self.list_all()
            if request.get("solicitante_id") == solicitante_id
        ]

    async def approve(self, transfer_id: str, data: dict[str, Any]) -> None:
        await self.update(transfer_id, {"status": "aprovada", **data})

    async def reject(self, transfer_id: str, data: dict[str, Any]) -> None:
        await self.update(transfer_id, {"status": "rejeitada", **data})

    async def cancel(self, transfer_id: str, data: dict[str, Any]) -> None:
        await self.update(transfer_id, {"status": "cancelada", **data})


class _FakeUserRepository(_FakeRepo):
    store: dict[str, dict[str, Any]] = {}

    def __init__(self, collection: str) -> None:
        self.collection = collection


def _coord() -> CurrentUser:
    return CurrentUser(
        uid="coord1",
        role="coordenacao",
        programa_id="prog",
        email="coord@saga.test",
    )


def _advisor_user() -> CurrentUser:
    return CurrentUser(
        uid="uid-origin",
        role="orientador",
        programa_id="prog",
        email="origem@saga.test",
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
    _FakeUserRepository.store = {
        "coord1": {
            "role": "coordenacao",
            "programa_id": "prog",
            "email": "coord@saga.test",
        },
    }
    monkeypatch.setattr(transfer_module, "StudentRepository", _FakeStudentRepository)
    monkeypatch.setattr(transfer_module, "AdvisorRepository", _FakeAdvisorRepository)
    monkeypatch.setattr(transfer_module, "TransferRepository", _FakeTransferRepository)
    monkeypatch.setattr(transfer_module, "FirebaseRepository", _FakeUserRepository)


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


async def test_direct_transfer_ignora_alunos_terminais_na_capacidade() -> None:
    _FakeAdvisorRepository.store["advisor2"]["limite_orientandos"] = 1
    _FakeStudentRepository.store["student2"] = {
        "orientador_id": "advisor2",
        "programa_id": "prog",
        "situacao_registrada": "concluido",
    }

    result = await TransferService().direct_transfer(
        DirectTransferRequest(student_id="student1", orientador_destino_id="advisor2"),
        _coord(),
    )

    assert result["orientador_destino_id"] == "advisor2"
    assert _FakeStudentRepository.store["student1"]["orientador_id"] == "advisor2"


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
            "tipo": "solicitada_orientador",
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


async def test_direct_transfer_invalida_nao_cancela_pendente() -> None:
    _FakeAdvisorRepository.store["advisor2"]["programa_id"] = "outro"
    _FakeTransferRepository.store = {
        "transfer_old": {
            "student_id": "student1",
            "status": "pendente",
            "tipo": "solicitada_orientador",
            "solicitante_id": "uid-origin",
            "programa_id": "prog",
        },
    }

    with pytest.raises(HTTPException) as exc_info:
        await TransferService().direct_transfer(
            DirectTransferRequest(student_id="student1", orientador_destino_id="advisor2"),
            _coord(),
        )

    assert exc_info.value.status_code == 400
    assert _FakeTransferRepository.store["transfer_old"]["status"] == "pendente"


async def test_direct_transfer_bloqueia_programa_diferente() -> None:
    _FakeAdvisorRepository.store["advisor2"]["programa_id"] = "outro"

    with pytest.raises(HTTPException) as exc_info:
        await TransferService().direct_transfer(
            DirectTransferRequest(student_id="student1", orientador_destino_id="advisor2"),
            _coord(),
        )

    assert exc_info.value.status_code == 400
    assert "mesmo programa" in str(exc_info.value.detail)


async def test_orientador_cria_solicitacao_para_orientando_proprio() -> None:
    result = await TransferService().create_request(
        TransferCreateRequest(student_id="student1", orientador_destino_id="advisor2"),
        _advisor_user(),
    )

    assert result["status"] == "pendente"
    assert result["orientador_origem_id"] == "advisor1"
    assert result["coord_uids"] == ["coord1"]
    assert _FakeTransferRepository.store[result["id"]]["status"] == "pendente"


async def test_orientador_nao_cria_solicitacao_para_aluno_de_outro_orientador() -> None:
    _FakeStudentRepository.store["student1"]["orientador_id"] = "advisor2"

    with pytest.raises(HTTPException) as exc_info:
        await TransferService().create_request(
            TransferCreateRequest(student_id="student1", orientador_destino_id="advisor3"),
            _advisor_user(),
        )

    assert exc_info.value.status_code == 403


async def test_segunda_solicitacao_pendente_retorna_409() -> None:
    _FakeTransferRepository.store = {
        "transfer_old": {
            "student_id": "student1",
            "status": "pendente",
            "solicitante_id": "uid-origin",
            "programa_id": "prog",
        },
    }

    with pytest.raises(HTTPException) as exc_info:
        await TransferService().create_request(
            TransferCreateRequest(student_id="student1", orientador_destino_id="advisor2"),
            _advisor_user(),
        )

    assert exc_info.value.status_code == 409


async def test_aprovacao_transfere_aluno_reaproveitando_efetivacao() -> None:
    _FakeTransferRepository.store = {
        "transfer1": {
            "student_id": "student1",
            "orientador_origem_id": "advisor1",
            "orientador_destino_id": "advisor2",
            "status": "pendente",
            "solicitante_id": "uid-origin",
            "programa_id": "prog",
        },
    }

    result = await TransferService().approve_request("transfer1", _coord())

    assert result["status"] == "aprovada"
    assert _FakeStudentRepository.store["student1"]["orientador_id"] == "advisor2"
    assert _FakeTransferRepository.store["transfer1"]["status"] == "aprovada"
    assert _FakeTransferRepository.store["transfer1"]["approved_by"] == "coord1"


async def test_rejeicao_exige_motivo() -> None:
    with pytest.raises(HTTPException) as exc_info:
        await TransferService().reject_request("transfer1", "  ", _coord())

    assert exc_info.value.status_code == 422


async def test_rejeicao_salva_motivo_e_decisor() -> None:
    _FakeTransferRepository.store = {
        "transfer1": {
            "student_id": "student1",
            "orientador_origem_id": "advisor1",
            "orientador_destino_id": "advisor2",
            "status": "pendente",
            "solicitante_id": "uid-origin",
            "programa_id": "prog",
        },
    }

    result = await TransferService().reject_request("transfer1", "Destino indisponivel", _coord())

    assert result["status"] == "rejeitada"
    assert _FakeTransferRepository.store["transfer1"]["motivo"] == "Destino indisponivel"
    assert _FakeTransferRepository.store["transfer1"]["rejected_by"] == "coord1"


async def test_cancelamento_so_funciona_para_solicitante_pendente() -> None:
    _FakeTransferRepository.store = {
        "transfer1": {
            "student_id": "student1",
            "orientador_origem_id": "advisor1",
            "orientador_destino_id": "advisor2",
            "status": "pendente",
            "solicitante_id": "uid-origin",
            "programa_id": "prog",
        },
    }

    result = await TransferService().cancel_request("transfer1", _advisor_user())

    assert result["status"] == "cancelada"
    assert _FakeTransferRepository.store["transfer1"]["status"] == "cancelada"
    assert _FakeTransferRepository.store["transfer1"]["cancelled_by"] == "uid-origin"


async def test_cancelamento_bloqueia_outro_orientador() -> None:
    _FakeTransferRepository.store = {
        "transfer1": {
            "student_id": "student1",
            "orientador_origem_id": "advisor1",
            "orientador_destino_id": "advisor2",
            "status": "pendente",
            "solicitante_id": "outro",
            "programa_id": "prog",
        },
    }

    with pytest.raises(HTTPException) as exc_info:
        await TransferService().cancel_request("transfer1", _advisor_user())

    assert exc_info.value.status_code == 403


async def test_listagem_filtra_por_papel() -> None:
    _FakeTransferRepository.store = {
        "transfer1": {
            "student_id": "student1",
            "status": "pendente",
            "solicitante_id": "uid-origin",
            "programa_id": "prog",
        },
        "transfer2": {
            "student_id": "student2",
            "status": "pendente",
            "solicitante_id": "outro",
            "programa_id": "prog",
        },
        "transfer3": {
            "student_id": "student3",
            "status": "pendente",
            "solicitante_id": "uid-origin",
            "programa_id": "outro",
        },
    }

    coord_result = await TransferService().list_requests(_coord())
    advisor_result = await TransferService().list_requests(_advisor_user())

    assert {item["id"] for item in coord_result} == {"transfer1", "transfer2"}
    assert {item["id"] for item in advisor_result} == {"transfer1", "transfer3"}
