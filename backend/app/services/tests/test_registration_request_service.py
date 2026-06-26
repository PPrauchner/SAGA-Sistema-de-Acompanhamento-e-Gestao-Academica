from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pytest
from fastapi import HTTPException

from backend.app.core.auth import CurrentUser
from backend.app.models.registration_request import (
    RegistrationRequestApprove,
    RegistrationRequestCreate,
    RegistrationRequestReject,
)
from backend.app.services.registration_request_service import RegistrationRequestService


class _FakeRegistrationRequestRepository:
    def __init__(self) -> None:
        self.store: dict[str, dict[str, Any]] = {}
        self.counter = 0

    async def create(self, data: dict[str, Any]) -> str:
        self.counter += 1
        request_id = f"req{self.counter}"
        self.store[request_id] = dict(data)
        return request_id

    async def get(self, request_id: str) -> dict[str, Any] | None:
        data = self.store.get(request_id)
        return {"id": request_id, **data} if data else None

    async def find_pending_by_email(self, email: str) -> dict[str, Any] | None:
        return next(
            (
                {"id": request_id, **data}
                for request_id, data in self.store.items()
                if data.get("email") == email and data.get("status") == "pendente"
            ),
            None,
        )

    async def list_pending_by_program(self, programa_id: str) -> list[dict[str, Any]]:
        return [
            {"id": request_id, **data}
            for request_id, data in self.store.items()
            if data.get("programa_id") == programa_id and data.get("status") == "pendente"
        ]

    async def approve(self, request_id: str, data: dict[str, Any]) -> bool:
        self.store[request_id].update({"status": "aprovado", **data})
        return True

    async def reject(self, request_id: str, data: dict[str, Any]) -> bool:
        self.store[request_id].update({"status": "rejeitado", **data})
        return True


class _FakeAdvisorRepository:
    def __init__(self) -> None:
        self.store = {
            "advisor1": {"id": "advisor1", "uid": "uid-advisor", "nome": "Profa. Ada", "programa_id": "prog"},
            "advisor2": {"id": "advisor2", "uid": "uid-other", "nome": "Prof. Alan", "programa_id": "outro"},
            "inactive": {"id": "inactive", "uid": None, "nome": "Sem Ativacao", "programa_id": "prog"},
        }

    async def get(self, advisor_id: str) -> dict[str, Any] | None:
        return self.store.get(advisor_id)

    async def list_all(self) -> list[dict[str, Any]]:
        return list(self.store.values())


class _FakeStudentService:
    def __init__(self) -> None:
        self.calls: list[tuple[Any, CurrentUser]] = []

    async def create_student(self, data: Any, user: CurrentUser) -> dict[str, Any]:
        self.calls.append((data, user))
        return {"id": "student1", "nome": data.nome, "invite_token": "tok-aluno"}


def _coord(programa_id: str = "prog") -> CurrentUser:
    return CurrentUser(uid="coord1", role="coordenacao", programa_id=programa_id, email="coord@saga.test")


def _service() -> tuple[RegistrationRequestService, _FakeRegistrationRequestRepository, _FakeStudentService]:
    repo = _FakeRegistrationRequestRepository()
    students = _FakeStudentService()
    return (
        RegistrationRequestService(
            repo=repo, advisor_repo=_FakeAdvisorRepository(), student_service=students
        ),
        repo,
        students,
    )


async def test_create_request_publica_deriva_programa_do_orientador() -> None:
    service, repo, _ = _service()

    result = await service.create_request(
        RegistrationRequestCreate(nome="Aluno", email="ALUNO@SAGA.TEST", advisor_id="advisor1")
    )

    assert result["status"] == "pendente"
    assert result["programa_id"] == "prog"
    assert result["orientador_id"] == "advisor1"
    assert result["orientador_nome"] == "Profa. Ada"
    assert repo.store["req1"]["email"] == "aluno@saga.test"


async def test_create_request_rejeita_orientador_inexistente() -> None:
    service, _, _ = _service()

    with pytest.raises(HTTPException) as exc_info:
        await service.create_request(
            RegistrationRequestCreate(nome="Aluno", email="aluno@saga.test", orientador_id="missing")
        )

    assert exc_info.value.status_code == 404


async def test_create_request_rejeita_orientador_nao_ativado() -> None:
    service, _, _ = _service()

    with pytest.raises(HTTPException) as exc_info:
        await service.create_request(
            RegistrationRequestCreate(nome="Aluno", email="aluno@saga.test", orientador_id="inactive")
        )

    assert exc_info.value.status_code == 400


async def test_create_request_rejeita_email_duplicado_pendente() -> None:
    service, _, _ = _service()
    payload = RegistrationRequestCreate(nome="Aluno", email="aluno@saga.test", orientador_id="advisor1")
    await service.create_request(payload)

    with pytest.raises(HTTPException) as exc_info:
        await service.create_request(payload)

    assert exc_info.value.status_code == 409


async def test_list_pending_filtra_programa_da_coordenacao() -> None:
    service, repo, _ = _service()
    repo.store = {
        "req1": {"nome": "A", "email": "a@test", "orientador_id": "advisor1", "programa_id": "prog", "status": "pendente", "created_at": datetime.now(timezone.utc)},
        "req2": {"nome": "B", "email": "b@test", "orientador_id": "advisor2", "programa_id": "outro", "status": "pendente", "created_at": datetime.now(timezone.utc)},
        "req3": {"nome": "C", "email": "c@test", "orientador_id": "advisor1", "programa_id": "prog", "status": "aprovado", "created_at": datetime.now(timezone.utc)},
    }

    result = await service.list_pending(_coord())

    assert [item["id"] for item in result] == ["req1"]


async def test_approve_cria_aluno_convite_e_marca_revisao() -> None:
    service, repo, students = _service()
    request = await service.create_request(
        RegistrationRequestCreate(nome="Aluno", email="aluno@saga.test", orientador_id="advisor1")
    )

    result = await service.approve_request(
        request["id"],
        RegistrationRequestApprove(matricula="2026001", data_ingresso=datetime(2026, 1, 1, tzinfo=timezone.utc)),
        _coord(),
    )

    student_payload, user = students.calls[0]
    assert student_payload.nome == "Aluno"
    assert student_payload.orientador_id == "advisor1"
    assert student_payload.programa_id == "prog"
    assert student_payload.matricula == "2026001"
    assert user.uid == "coord1"
    assert result["status"] == "aprovado"
    assert result["reviewed_by"] == "coord1"
    assert result["reviewed_at"] is not None
    assert repo.store[request["id"]]["student_id"] == "student1"
    assert repo.store[request["id"]]["invite_token"] == "tok-aluno"


async def test_approve_bloqueia_outro_programa() -> None:
    service, _, _ = _service()
    request = await service.create_request(
        RegistrationRequestCreate(nome="Aluno", email="aluno@saga.test", orientador_id="advisor1")
    )

    with pytest.raises(HTTPException) as exc_info:
        await service.approve_request(request["id"], RegistrationRequestApprove(), _coord("outro"))

    assert exc_info.value.status_code == 403


async def test_reject_marca_revisao_e_motivo() -> None:
    service, repo, _ = _service()
    request = await service.create_request(
        RegistrationRequestCreate(nome="Aluno", email="aluno@saga.test", orientador_id="advisor1")
    )

    result = await service.reject_request(
        request["id"],
        RegistrationRequestReject(motivo="Documentacao incompleta"),
        _coord(),
    )

    assert result["status"] == "rejeitado"
    assert result["reviewed_by"] == "coord1"
    assert result["reviewed_at"] is not None
    assert repo.store[request["id"]]["rejection_reason"] == "Documentacao incompleta"


async def test_review_bloqueia_solicitacao_nao_pendente() -> None:
    service, _, _ = _service()
    request = await service.create_request(
        RegistrationRequestCreate(nome="Aluno", email="aluno@saga.test", orientador_id="advisor1")
    )
    await service.reject_request(request["id"], RegistrationRequestReject(), _coord())

    with pytest.raises(HTTPException) as exc_info:
        await service.approve_request(request["id"], RegistrationRequestApprove(), _coord())

    assert exc_info.value.status_code == 409
