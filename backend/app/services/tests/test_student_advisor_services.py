from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pytest
from fastapi import HTTPException

from backend.app.aspects import aspect_config
from backend.app.core.auth import CurrentUser
from backend.app.models.advisor import AdvisorCreateRequest
from backend.app.models.student import SituacaoRequest, StudentCreateRequest
from backend.app.models.user import InviteRequest
from backend.app.services import advisor_service as advisor_module
from backend.app.services import student_service as student_module
from backend.app.services.advisor_service import AdvisorService
from backend.app.services.student_service import StudentService


class _FakeRepo:
    store: dict[str, dict[str, Any]] = {}
    prefix = "doc"
    counter = 0

    def __init__(self) -> None:
        pass

    async def create(self, data: dict[str, Any]) -> str:
        type(self).counter += 1
        doc_id = f"{self.prefix}{type(self).counter}"
        type(self).store[doc_id] = dict(data)
        return doc_id

    async def get(self, doc_id: str) -> dict[str, Any] | None:
        data = type(self).store.get(doc_id)
        return dict(data) if data else None

    async def set(self, doc_id: str, data: dict[str, Any]) -> None:
        type(self).store[doc_id] = dict(data)

    async def update(self, doc_id: str, data: dict[str, Any]) -> None:
        type(self).store.setdefault(doc_id, {}).update(data)

    async def delete(self, doc_id: str) -> None:
        type(self).store.pop(doc_id, None)

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

    async def get_advisors_with_student_count(self) -> list[dict[str, Any]]:
        advisors = await self.list_all()
        students = await _FakeStudentRepository().list_all()
        for advisor in advisors:
            advisor["orientandos_ativos"] = sum(
                1 for student in students if student.get("orientador_id") == advisor["id"]
            )
        return advisors

    async def count_active_students(self, advisor_id: str) -> int:
        students = await _FakeStudentRepository().list_all()
        return sum(
            1
            for student in students
            if student.get("orientador_id") == advisor_id
            and student.get("situacao_registrada") not in {"concluido", "desligado"}
        )


class _FakeAuthService:
    async def create_invite(
        self,
        data: InviteRequest,
        current_user: CurrentUser,
        extra_fields: dict[str, Any] | None = None,
    ):
        return type("Invite", (), {"token": f"tok-{data.role}", "expira_em": "x"})()


def _coord() -> CurrentUser:
    return CurrentUser(uid="coord1", role="coordenacao", programa_id="prog", email="c@x.com")


def _advisor_user() -> CurrentUser:
    return CurrentUser(uid="uid-advisor", role="orientador", programa_id="prog", email="a@x.com")


@pytest.fixture(autouse=True)
def _setup(monkeypatch: pytest.MonkeyPatch) -> None:
    _FakeStudentRepository.store = {}
    _FakeStudentRepository.counter = 0
    _FakeAdvisorRepository.store = {}
    _FakeAdvisorRepository.counter = 0
    monkeypatch.setattr(aspect_config, "AUDIT_ENABLED", False)
    monkeypatch.setattr(student_module, "StudentRepository", _FakeStudentRepository)
    monkeypatch.setattr(student_module, "AdvisorRepository", _FakeAdvisorRepository)
    monkeypatch.setattr(advisor_module, "StudentRepository", _FakeStudentRepository)
    monkeypatch.setattr(advisor_module, "AdvisorRepository", _FakeAdvisorRepository)


async def test_create_student_usa_auto_id_e_retorna_invite_token() -> None:
    service = StudentService(auth_service=_FakeAuthService())
    data_ingresso = datetime(2024, 3, 31, tzinfo=timezone.utc)

    result = await service.create_student(
        StudentCreateRequest(
            nome="Aluno X",
            email="aluno@x.com",
            matricula="2024001",
            orientador_id="advisor1",
            nivel="mestrado",
            data_ingresso=data_ingresso,
            programa_id="prog",
        ),
        _coord(),
    )

    assert result["id"] == "student1"
    assert result["invite_token"] == "tok-aluno"
    assert "2024001" not in _FakeStudentRepository.store
    assert _FakeStudentRepository.store["student1"]["matricula"] == "2024001"
    assert _FakeStudentRepository.store["student1"]["prazo_final"] == datetime(
        2026,
        3,
        31,
        tzinfo=timezone.utc,
    )


async def test_list_students_orientador_filtra_por_auto_id_do_advisor() -> None:
    _FakeAdvisorRepository.store = {
        "advisor1": {"uid": "uid-advisor", "nome": "Orientador"},
        "advisor2": {"uid": "outro", "nome": "Outro"},
    }
    _FakeStudentRepository.store = {
        "student1": {"nome": "Meu aluno", "orientador_id": "advisor1"},
        "student2": {"nome": "Outro aluno", "orientador_id": "advisor2"},
    }
    service = StudentService(auth_service=_FakeAuthService())

    result = await service.list_students(_advisor_user())

    assert [student["id"] for student in result] == ["student1"]


async def test_get_student_orientador_filtra_por_propriedade() -> None:
    _FakeAdvisorRepository.store = {
        "advisor1": {"uid": "uid-advisor", "nome": "Orientador"},
        "advisor2": {"uid": "outro", "nome": "Outro"},
    }
    _FakeStudentRepository.store = {
        "student1": {"nome": "Meu aluno", "orientador_id": "advisor1"},
        "student2": {"nome": "Outro aluno", "orientador_id": "advisor2"},
    }
    service = StudentService(auth_service=_FakeAuthService())

    result = await service.get_student("student1", _advisor_user())

    assert result["id"] == "student1"

    with pytest.raises(HTTPException) as exc_info:
        await service.get_student("student2", _advisor_user())

    assert exc_info.value.status_code == 403


async def test_update_situacao_nao_grava_observacao_no_documento() -> None:
    _FakeStudentRepository.store = {
        "student1": {"nome": "Aluno", "situacao_registrada": "regular"},
    }
    service = StudentService(auth_service=_FakeAuthService())

    await service.update_situacao(
        "student1",
        SituacaoRequest(
            situacao_registrada="em_risco",
            observacao="Acompanhar no historico",
        ),
        _coord(),
    )

    assert _FakeStudentRepository.store["student1"]["situacao_registrada"] == "em_risco"
    assert "situacao_observacao" not in _FakeStudentRepository.store["student1"]


async def test_create_advisor_usa_auto_id_e_retorna_invite_token() -> None:
    service = AdvisorService(auth_service=_FakeAuthService())

    result = await service.create_advisor(
        AdvisorCreateRequest(
            nome="Orientador X",
            email="orientador@x.com",
            departamento="Computação",
            programa_id="prog",
        ),
        _coord(),
    )

    assert result["id"] == "advisor1"
    assert result["invite_token"] == "tok-orientador"
    assert "orientador@x.com" not in _FakeAdvisorRepository.store
    assert _FakeAdvisorRepository.store["advisor1"]["email"] == "orientador@x.com"


async def test_get_advisor_retorna_orientandos_ativos() -> None:
    _FakeAdvisorRepository.store = {
        "advisor1": {"uid": "uid-advisor", "nome": "Orientador"},
    }
    _FakeStudentRepository.store = {
        "student1": {"orientador_id": "advisor1", "situacao_registrada": "regular"},
        "student2": {"orientador_id": "advisor1", "situacao_registrada": "concluido"},
        "student3": {"orientador_id": "advisor2", "situacao_registrada": "regular"},
    }
    service = AdvisorService(auth_service=_FakeAuthService())

    result = await service.get_advisor("advisor1")

    assert result["orientandos_ativos"] == 1
