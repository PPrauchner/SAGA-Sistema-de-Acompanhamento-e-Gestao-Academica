"""
Testes dos endpoints GET /checklist/{id} e GET /inference/{id} (issues #43 e #127).

Monta um app FastAPI mínimo com apenas os dois routers para isolar o teste das demais
dependências (Firebase, settings). Verifica:
- resposta 200 com dados-fixture e 404 para aluno inexistente (coordenação);
- a guarda de autorização AOP da issue #127: aluno só acessa o próprio student_id,
  orientador só seus orientandos, coordenação livre — 403 nos demais casos.

A dependência get_current_user é sobrescrita por teste para injetar o papel. A
verificação de propriedade lê de FirebaseRepository dentro do aspecto ownership, então
esse repositório é mockado nos cenários de aluno/orientador. AUDIT_ENABLED é desligado
para evitar acesso real ao Firestore pelo @audit_operation do endpoint de inferência.
"""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.app.api.v1 import checklist, inference
from backend.app.core.auth import CurrentUser, get_current_user
from backend.app.repositories.fixtures import FixtureRepository
from backend.app.services.checklist_service import ChecklistService
from backend.app.services.inference_service import InferenceService

COORDENACAO = CurrentUser(uid="uid_coord", role="coordenacao", programa_id="p1")


def _mock_inference_service() -> InferenceService:
    return InferenceService(FixtureRepository())


def _mock_checklist_service() -> ChecklistService:
    repo = FixtureRepository()
    return ChecklistService(InferenceService(repo), repo)


def _build_client(user: CurrentUser) -> TestClient:
    app = FastAPI()
    app.include_router(checklist.router, prefix="/api/v1")
    app.include_router(inference.router, prefix="/api/v1")
    app.dependency_overrides[checklist._get_checklist_service] = _mock_checklist_service
    app.dependency_overrides[inference._get_inference_service] = _mock_inference_service
    app.dependency_overrides[get_current_user] = lambda: user
    return TestClient(app)


@pytest.fixture(autouse=True)
def _disable_audit():
    """Desliga @audit_operation para não tocar o Firestore real durante o teste."""
    with patch("backend.app.aspects.aspect_config.AUDIT_ENABLED", False):
        yield


@pytest.fixture
def client() -> TestClient:
    return _build_client(COORDENACAO)


def test_get_checklist_ok(client: TestClient) -> None:
    response = client.get("/api/v1/checklist/aluno_risco")
    assert response.status_code == 200
    body = response.json()
    assert body["student_id"] == "aluno_risco"
    assert body["conflito_situacao"] is True
    assert body["situacao_inferida"] == "em_risco"
    assert set(body["requisitos"]) == {
        "creditos_minimos",
        "creditos_grupo_basico",
        "creditos_grupo_especifico",
        "creditos_grupo_tecnologico",
        "proficiencia",
        "qualificacao",
        "producao_validada",
        "plano_concluido",
    }


def test_get_inference_ok(client: TestClient) -> None:
    response = client.get("/api/v1/inference/aluno_apto")
    assert response.status_code == 200
    body = response.json()
    assert body["apto_defesa"] is True
    assert body["situacao_inferida"] == "em_fase_de_defesa"
    assert body["fatos_usados"]
    assert body["pontuacoes_producoes"][0]["score"] == 10.0


def test_get_checklist_404(client: TestClient) -> None:
    response = client.get("/api/v1/checklist/inexistente")
    assert response.status_code == 404


def test_get_inference_404(client: TestClient) -> None:
    response = client.get("/api/v1/inference/inexistente")
    assert response.status_code == 404


# --- Autorização AOP (issue #127) -----------------------------------------
# A propriedade é verificada pelo aspecto ownership, que lê o aluno via
# FirebaseRepository; mockamos esse repositório para controlar uid/orientador_id.


@pytest.fixture(autouse=True)
def _enable_authorization():
    with patch("backend.app.aspects.aspect_config.AUTHORIZATION_ENABLED", True):
        yield


def _mock_ownership_repo(student_doc: dict, advisor_docs: list[dict] | None = None):
    """Patch de FirebaseRepository no módulo ownership com docs controlados."""
    repo = AsyncMock()
    repo.get.return_value = student_doc
    repo.query.return_value = advisor_docs or []
    patcher = patch("backend.app.aspects.ownership.FirebaseRepository", return_value=repo)
    return patcher


@pytest.mark.parametrize("path", ["/api/v1/checklist/aluno_risco", "/api/v1/inference/aluno_risco"])
def test_aluno_acessa_proprio_200(path: str) -> None:
    aluno = CurrentUser(uid="uid_aluno", role="aluno", programa_id="p1")
    client = _build_client(aluno)
    with _mock_ownership_repo({"id": "aluno_risco", "uid": "uid_aluno"}):
        response = client.get(path)
    assert response.status_code == 200


@pytest.mark.parametrize("path", ["/api/v1/checklist/aluno_risco", "/api/v1/inference/aluno_risco"])
def test_aluno_acessa_terceiro_403(path: str) -> None:
    aluno = CurrentUser(uid="uid_aluno", role="aluno", programa_id="p1")
    client = _build_client(aluno)
    with _mock_ownership_repo({"id": "aluno_risco", "uid": "uid_outro"}):
        response = client.get(path)
    assert response.status_code == 403


@pytest.mark.parametrize("path", ["/api/v1/checklist/aluno_risco", "/api/v1/inference/aluno_risco"])
def test_orientador_acessa_orientando_200(path: str) -> None:
    orientador = CurrentUser(uid="uid_ori", role="orientador", programa_id="p1")
    client = _build_client(orientador)
    student_doc = {"id": "aluno_risco", "uid": "uid_x", "orientador_id": "adv_1"}
    advisor_docs = [{"id": "adv_1", "uid": "uid_ori"}]
    with _mock_ownership_repo(student_doc, advisor_docs):
        response = client.get(path)
    assert response.status_code == 200


@pytest.mark.parametrize("path", ["/api/v1/checklist/aluno_risco", "/api/v1/inference/aluno_risco"])
def test_orientador_acessa_nao_orientando_403(path: str) -> None:
    orientador = CurrentUser(uid="uid_ori", role="orientador", programa_id="p1")
    client = _build_client(orientador)
    student_doc = {"id": "aluno_risco", "uid": "uid_x", "orientador_id": "adv_2"}
    advisor_docs = [{"id": "adv_1", "uid": "uid_ori"}]
    with _mock_ownership_repo(student_doc, advisor_docs):
        response = client.get(path)
    assert response.status_code == 403
