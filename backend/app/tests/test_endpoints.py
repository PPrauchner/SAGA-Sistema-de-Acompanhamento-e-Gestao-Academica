"""
Testes dos endpoints GET /checklist/{id} e GET /inference/{id} (issue #43).

Monta um app FastAPI mínimo com apenas os dois routers para isolar o teste das demais
dependências (Firebase, settings). Verifica resposta 200 com dados-fixture e 404 para
aluno inexistente.
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.app.api.v1 import checklist, inference
from backend.app.core.auth import CurrentUser, get_current_user
from backend.app.repositories.fixtures import FixtureRepository
from backend.app.services.inference_service import InferenceService
from backend.app.services.checklist_service import ChecklistService


def _mock_inference_service() -> InferenceService:
    return InferenceService(FixtureRepository())


def _mock_checklist_service() -> ChecklistService:
    repo = FixtureRepository()
    return ChecklistService(InferenceService(repo), repo)


def _mock_current_user() -> CurrentUser:
    return CurrentUser(uid="u-coord", role="coordenacao", programa_id="prog", email="c@x.com")


@pytest.fixture
def client() -> TestClient:
    app = FastAPI()
    app.include_router(checklist.router, prefix="/api/v1")
    app.include_router(inference.router, prefix="/api/v1")
    app.dependency_overrides[checklist._get_checklist_service] = _mock_checklist_service
    app.dependency_overrides[inference._get_inference_service] = _mock_inference_service
    app.dependency_overrides[get_current_user] = _mock_current_user
    return TestClient(app)


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
