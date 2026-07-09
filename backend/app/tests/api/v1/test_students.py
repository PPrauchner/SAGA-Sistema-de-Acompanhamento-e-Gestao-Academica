from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

os.environ.setdefault("FIREBASE_PROJECT_ID", "test-project")
os.environ.setdefault("FIREBASE_PRIVATE_KEY", "test-key")
os.environ.setdefault("FIREBASE_CLIENT_EMAIL", "test@test-project.iam.gserviceaccount.com")

import pytest
from fastapi.testclient import TestClient

from backend.app.aspects import aspect_config
from backend.app.api.v1 import students as students_router
from backend.app.core.auth import CurrentUser, get_current_user
from backend.app.main import app


class _FakeStudentRepository:
    def __init__(self, store: dict[str, dict[str, Any]]) -> None:
        self.store = store

    async def list_all(self) -> list[dict[str, Any]]:
        return [{"id": key, **value} for key, value in self.store.items()]

    async def get(self, student_id: str) -> dict[str, Any] | None:
        student = self.store.get(student_id)
        return {"id": student_id, **student} if student is not None else None

    async def list_by_program(self, programa_id: str) -> list[dict[str, Any]]:
        return [
            {"id": key, **value}
            for key, value in self.store.items()
            if value.get("programa_id") == programa_id
        ]


class _FakeStudentService:
    def __init__(self) -> None:
        self.user: CurrentUser | None = None
        self.body: Any | None = None

    async def create_student(self, body: Any, user: CurrentUser) -> dict[str, Any]:
        self.body = body
        self.user = user
        return {"id": "student1", "nome": body.nome, "invite_token": "tok-aluno"}


def _coord() -> CurrentUser:
    return CurrentUser(uid="coord1", role="coordenacao", programa_id="prog", email="coord@saga.edu")


def _advisor() -> CurrentUser:
    return CurrentUser(uid="advisor1", role="orientador", programa_id="prog", email="advisor@saga.edu")


def _legacy_student() -> dict[str, Any]:
    return {
        "nome": "Aluno Legado",
        "email": "legado@saga.edu",
        "matricula": "2026001",
        "orientador_id": "advisor1",
        "programa_id": "prog",
        "nivel": "mestrado",
        "data_ingresso": datetime(2026, 1, 1, tzinfo=timezone.utc),
    }


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    original_students = students_router.service._students
    monkeypatch.setattr(aspect_config, "AUDIT_ENABLED", False)
    app.dependency_overrides[get_current_user] = _coord
    yield TestClient(app)
    students_router.service._students = original_students
    app.dependency_overrides.clear()


def test_get_students_response_model_normaliza_documento_legado(client: TestClient) -> None:
    students_router.service._students = _FakeStudentRepository({"student1": _legacy_student()})

    response = client.get("/api/v1/students")

    assert response.status_code == 200
    body = response.json()
    assert body == [
        {
            "id": "student1",
            "nome": "Aluno Legado",
            "email": "legado@saga.edu",
            "matricula": "2026001",
            "orientador_id": "advisor1",
            "coorientador_id": None,
            "programa_id": "prog",
            "nivel": "mestrado",
            "situacao_registrada": "regular",
            "situacao_inferida": "regular",
            "data_ingresso": "2026-01-01T00:00:00Z",
            "prazo_final": None,
            "qualificacao_aprovada": False,
            "proficiencia_comprovada": False,
            "qualificacao_data": None,
            "proficiencia_data": None,
        },
    ]


def test_get_student_response_model_normaliza_documento_legado(client: TestClient) -> None:
    students_router.service._students = _FakeStudentRepository({"student1": _legacy_student()})

    response = client.get("/api/v1/students/student1")

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == "student1"
    assert body["situacao_registrada"] == "regular"
    assert body["situacao_inferida"] == "regular"
    assert body["qualificacao_aprovada"] is False
    assert body["proficiencia_comprovada"] is False
    assert body["coorientador_id"] is None


def _aluno() -> CurrentUser:
    return CurrentUser(uid="uid-aluno1", role="aluno", programa_id="prog", email="aluno@saga.edu")


def test_get_students_coauthors_acessivel_a_aluno(client: TestClient) -> None:
    students_router.service._students = _FakeStudentRepository(
        {
            "student1": {"uid": "uid-aluno1", "nome": "Aluno 1", "programa_id": "prog"},
            "student2": {"uid": "uid-aluno2", "nome": "Aluno 2", "programa_id": "prog"},
            "student3": {"uid": "uid-outro-prog", "nome": "Outro programa", "programa_id": "outro"},
        }
    )
    app.dependency_overrides[get_current_user] = _aluno

    response = client.get("/api/v1/students/coauthors")

    assert response.status_code == 200
    assert response.json() == [
        {"uid": "uid-aluno1", "nome": "Aluno 1"},
        {"uid": "uid-aluno2", "nome": "Aluno 2"},
    ]


def test_get_students_bloqueia_aluno(client: TestClient) -> None:
    app.dependency_overrides[get_current_user] = _aluno

    response = client.get("/api/v1/students")

    assert response.status_code == 403


def test_post_students_permite_orientador(client: TestClient) -> None:
    fake_service = _FakeStudentService()
    original_service = students_router.service
    students_router.service = fake_service
    app.dependency_overrides[get_current_user] = _advisor

    response = client.post(
        "/api/v1/students",
        json={
            "nome": "Novo Aluno",
            "email": "novo@saga.edu",
            "matricula": "2026002",
            "orientador_id": "advisor1",
            "coorientador_id": None,
            "nivel": "mestrado",
            "data_ingresso": "2026-01-01T00:00:00Z",
            "programa_id": "prog",
        },
    )

    students_router.service = original_service
    app.dependency_overrides[get_current_user] = _coord

    assert response.status_code == 201
    assert response.json()["invite_token"] == "tok-aluno"
    assert fake_service.user is not None
    assert fake_service.user.role == "orientador"


def test_post_students_sem_nivel_usa_default_mestrado(client: TestClient) -> None:
    fake_service = _FakeStudentService()
    original_service = students_router.service
    students_router.service = fake_service

    response = client.post(
        "/api/v1/students",
        json={
            "nome": "Novo Aluno",
            "email": "novo@saga.edu",
            "matricula": "2026003",
            "orientador_id": "advisor1",
            "coorientador_id": None,
            "data_ingresso": "2026-01-01T00:00:00Z",
            "programa_id": "prog",
        },
    )

    students_router.service = original_service

    assert response.status_code == 201
    assert fake_service.body is not None
    assert fake_service.body.nivel == "mestrado"
