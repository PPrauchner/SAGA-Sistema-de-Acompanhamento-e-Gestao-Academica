"""
Testes da camada HTTP do router de prorrogações (Spec 08).

Exercita as quatro rotas reais (POST /extensions, GET /extensions,
PATCH /{id}/review, PATCH /{id}/approve) com o ExtensionService substituído via
`app.dependency_overrides[get_extension_service]`. A lógica de negócio é coberta
em backend/app/services/tests/test_extension_service.py — aqui o alvo é o
roteamento, a serialização do contrato e o gate de papel do aspecto A01.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pytest
from fastapi.testclient import TestClient

from backend.app.api.v1.extensions import get_extension_service
from backend.app.aspects import aspect_config
from backend.app.core.auth import CurrentUser, get_current_user
from backend.app.main import app
from backend.app.models.extension import ExtensionResponse

PRAZO_NOVO = datetime(2028, 7, 1, tzinfo=timezone.utc)
MOTIVO = "Motivo longo o suficiente para passar na validacao"
PARECER = "Parecer tecnico favoravel do orientador"


def _response(extension_id: str = "ext1", status: str = "pendente") -> ExtensionResponse:
    return ExtensionResponse(
        id=extension_id,
        student_id="student1",
        requester_id="uid-aluno",
        programa_id="prog",
        tipo="prazo_defesa",
        motivo=MOTIVO,
        plano_atualizado="http://plano.test/doc.pdf",
        status=status,
        nova_data=PRAZO_NOVO,
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        student_nome="Aluno Um",
    )


class _FakeExtensionService:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []

    async def create_extension(self, payload: Any, requester_uid: str) -> ExtensionResponse:
        self.calls.append(("create", {"payload": payload, "requester_uid": requester_uid}))
        return _response("ext_new")

    async def list_for_user(self, user: CurrentUser) -> list[ExtensionResponse]:
        self.calls.append(("list", {"user": user}))
        return [_response()]

    async def add_review(self, extension_id: str, payload: Any, orientador_uid: str) -> ExtensionResponse:
        self.calls.append(
            ("review", {"extension_id": extension_id, "payload": payload, "orientador_uid": orientador_uid})
        )
        return _response()

    async def process_decision(
        self, extension_id: str, payload: Any, coordinator: CurrentUser
    ) -> ExtensionResponse:
        self.calls.append(
            ("decide", {"extension_id": extension_id, "payload": payload, "coordinator": coordinator})
        )
        return _response(status="aprovada")


def _user(role: str) -> CurrentUser:
    return CurrentUser(uid=f"uid-{role}", role=role, programa_id="prog", email=f"{role}@saga.test")


def _valid_payload() -> dict[str, Any]:
    return {
        "tipo": "prazo_defesa",
        "motivo": MOTIVO,
        "plano_atualizado": "http://plano.test/doc.pdf",
        "nova_data": PRAZO_NOVO.isoformat(),
    }


@pytest.fixture
def service() -> _FakeExtensionService:
    return _FakeExtensionService()


@pytest.fixture
def client(service: _FakeExtensionService, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(aspect_config, "ALERTS_ENABLED", False)
    app.dependency_overrides[get_extension_service] = lambda: service
    yield TestClient(app)
    app.dependency_overrides.clear()


def _as(role: str) -> None:
    app.dependency_overrides[get_current_user] = lambda: _user(role)


# ---------------------------------------------------------------------------
# POST /extensions — solicitação (aluno)
# ---------------------------------------------------------------------------

def test_post_extensions_aluno_cria_solicitacao(client: TestClient, service: _FakeExtensionService) -> None:
    _as("aluno")

    response = client.post("/api/v1/extensions", json=_valid_payload())

    assert response.status_code == 201
    assert response.json()["id"] == "ext_new"
    name, kwargs = service.calls[0]
    assert name == "create"
    # O router repassa o uid do autenticado; nunca aceita student_id do corpo.
    assert kwargs["requester_uid"] == "uid-aluno"


@pytest.mark.parametrize("role", ["orientador", "coordenacao"])
def test_post_extensions_bloqueia_papel_nao_aluno(client: TestClient, role: str) -> None:
    _as(role)

    response = client.post("/api/v1/extensions", json=_valid_payload())

    assert response.status_code == 403


def test_post_extensions_422_sem_plano_atualizado(client: TestClient) -> None:
    """plano_atualizado é obrigatório (Spec 08): payload legado deve ser rejeitado."""
    _as("aluno")
    payload = _valid_payload()
    del payload["plano_atualizado"]

    response = client.post("/api/v1/extensions", json=payload)

    assert response.status_code == 422


def test_post_extensions_422_motivo_curto(client: TestClient) -> None:
    _as("aluno")

    response = client.post("/api/v1/extensions", json={**_valid_payload(), "motivo": "curto"})

    assert response.status_code == 422


# ---------------------------------------------------------------------------
# GET /extensions — listagem (escopo por papel resolvido no service)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("role", ["aluno", "orientador", "coordenacao"])
def test_get_extensions_permitido_para_os_tres_papeis(
    client: TestClient, service: _FakeExtensionService, role: str
) -> None:
    _as(role)

    response = client.get("/api/v1/extensions")

    assert response.status_code == 200
    body = response.json()
    assert body[0]["id"] == "ext1"
    assert body[0]["student_nome"] == "Aluno Um"
    # O escopo é decidido no service a partir do usuário autenticado.
    assert service.calls[0][1]["user"].role == role


# ---------------------------------------------------------------------------
# PATCH /extensions/{id}/review — parecer (orientador)
# ---------------------------------------------------------------------------

def test_patch_review_orientador_registra_parecer(
    client: TestClient, service: _FakeExtensionService
) -> None:
    _as("orientador")

    response = client.patch("/api/v1/extensions/ext1/review", json={"parecer_orientador": PARECER})

    assert response.status_code == 200
    name, kwargs = service.calls[0]
    assert name == "review"
    assert kwargs["extension_id"] == "ext1"
    assert kwargs["orientador_uid"] == "uid-orientador"


@pytest.mark.parametrize("role", ["aluno", "coordenacao"])
def test_patch_review_bloqueia_papel_nao_orientador(client: TestClient, role: str) -> None:
    _as(role)

    response = client.patch("/api/v1/extensions/ext1/review", json={"parecer_orientador": PARECER})

    assert response.status_code == 403


def test_patch_review_422_parecer_curto(client: TestClient) -> None:
    _as("orientador")

    response = client.patch("/api/v1/extensions/ext1/review", json={"parecer_orientador": "curto"})

    assert response.status_code == 422


# ---------------------------------------------------------------------------
# PATCH /extensions/{id}/approve — decisão (coordenação)
# ---------------------------------------------------------------------------

def test_patch_approve_coordenacao_homologa(client: TestClient, service: _FakeExtensionService) -> None:
    _as("coordenacao")

    response = client.patch("/api/v1/extensions/ext1/approve", json={"acao": "aprovar"})

    assert response.status_code == 200
    assert response.json()["status"] == "aprovada"
    name, kwargs = service.calls[0]
    assert name == "decide"
    # O router repassa o CurrentUser inteiro: o service precisa do programa_id
    # para barrar deliberação cross-programa, não só do uid.
    assert kwargs["coordinator"].uid == "uid-coordenacao"
    assert kwargs["coordinator"].programa_id == "prog"


@pytest.mark.parametrize("role", ["aluno", "orientador"])
def test_patch_approve_bloqueia_papel_nao_coordenacao(client: TestClient, role: str) -> None:
    _as(role)

    response = client.patch("/api/v1/extensions/ext1/approve", json={"acao": "aprovar"})

    assert response.status_code == 403


def test_patch_approve_422_acao_invalida(client: TestClient) -> None:
    _as("coordenacao")

    response = client.patch("/api/v1/extensions/ext1/approve", json={"acao": "talvez"})

    assert response.status_code == 422
