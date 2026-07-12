from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from datetime import date

from backend.app.api.v1.extensions import _build_notificacao_aprovacao
from backend.app.aspects import aspect_config
from backend.app.core.auth import CurrentUser, get_current_user
from backend.app.main import app


class _FakeExtensionService:
    calls: list[tuple[str, ...]] = []

    async def approve_extension(self, extension_id: str, user: CurrentUser) -> dict[str, Any]:
        self.calls.append(("approve", extension_id, user.uid))
        return {
            "id": extension_id,
            "tipo": "prazo_defesa",
            "status": "aprovada",
            "student_id": "student1",
            "aluno_id": "student1",
            "aluno_uid": "uid-aluno",
            "aluno_nome": "Aluno Um",
            "aluno": "Aluno Um",
            "created_at": "2026-01-01T00:00:00+00:00",
            "solicitacao": "2026-01-01T00:00:00+00:00",
            "motivo": "Ajuste",
            "justificativa": "Ajuste",
        }

    async def reject_extension(
        self, extension_id: str, motivo: str, user: CurrentUser
    ) -> dict[str, Any]:
        self.calls.append(("reject", extension_id, user.uid, motivo))
        return {
            "id": extension_id,
            "tipo": "prazo_defesa",
            "status": "rejeitada",
            "student_id": "student1",
            "aluno_id": "student1",
            "aluno_nome": "Aluno Um",
            "aluno": "Aluno Um",
            "created_at": "2026-01-01T00:00:00+00:00",
            "solicitacao": "2026-01-01T00:00:00+00:00",
            "motivo": "Ajuste",
            "justificativa": "Ajuste",
        }


def _override_user(role: str) -> None:
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        uid=f"uid-{role}",
        role=role,
        programa_id="prog",
        email=f"{role}@saga.test",
    )


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    fake_service = _FakeExtensionService()
    _FakeExtensionService.calls = []
    monkeypatch.setattr("backend.app.api.v1.extensions.service", fake_service)
    monkeypatch.setattr(aspect_config, "AUDIT_ENABLED", False)
    monkeypatch.setattr(aspect_config, "ALERTS_ENABLED", False)
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_coordenacao_aprova_e_rejeita_extension(client: TestClient) -> None:
    _override_user("coordenacao")

    approved = client.post("/api/v1/extensions/ext1/approve")
    rejected = client.post(
        "/api/v1/extensions/ext2/reject",
        json={"motivo": "Sem justificativa suficiente"},
    )

    assert approved.status_code == 200
    assert approved.json()["status"] == "aprovada"
    assert rejected.status_code == 200
    assert rejected.json()["status"] == "rejeitada"
    assert ("approve", "ext1", "uid-coordenacao") in _FakeExtensionService.calls
    assert (
        "reject",
        "ext2",
        "uid-coordenacao",
        "Sem justificativa suficiente",
    ) in _FakeExtensionService.calls


@pytest.mark.parametrize("role", ["aluno", "orientador"])
def test_papeis_nao_coordenacao_nao_decidem_extension(
    client: TestClient,
    role: str,
) -> None:
    _override_user(role)

    approved = client.post("/api/v1/extensions/ext1/approve")
    rejected = client.post(
        "/api/v1/extensions/ext1/reject", json={"motivo": "x"}
    )

    assert approved.status_code == 403
    assert rejected.status_code == 403
    assert _FakeExtensionService.calls == []


def test_build_notificacao_aprovacao_notifica_aluno_com_novo_prazo() -> None:
    result = {
        "id": "ext1",
        "tipo": "prazo_defesa",
        "status": "aprovada",
        "aluno_uid": "uid-aluno",
        "nova_data": date(2027, 3, 10),
        "programa_id": "prog",
    }

    spec = _build_notificacao_aprovacao(result, (), {})

    assert spec is not None
    assert spec["tipo"] == "prorrogacao_aprovada"
    assert spec["destinatario_id"] == "uid-aluno"
    assert spec["entidade_tipo"] == "extensions"
    assert spec["entidade_id"] == "ext1"
    assert "10/03/2027" in spec["mensagem"]


def test_build_notificacao_aprovacao_sem_aluno_nao_emite() -> None:
    assert _build_notificacao_aprovacao({"status": "aprovada"}, (), {}) is None
    assert _build_notificacao_aprovacao(None, (), {}) is None
