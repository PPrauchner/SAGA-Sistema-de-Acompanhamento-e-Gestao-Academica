"""
Testes para os endpoints da API de Programas.

Responsabilidades:
- Verificar o endpoint GET de listagem de programas.
- Verificar os endpoints GET e PUT para a configuração do programa.
- Garantir a integração correta com o ProgramService.
"""

import os
from unittest.mock import AsyncMock, patch

# Set dummy environment variables to satisfy pydantic-settings
os.environ["FIREBASE_PROJECT_ID"] = "test-project"
os.environ["FIREBASE_PRIVATE_KEY"] = "test-key"
os.environ["FIREBASE_CLIENT_EMAIL"] = "test-email"

import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.core.auth import get_current_user
from backend.app.services.program_service import ProgramService

client = TestClient(app)


def _override_auth_and_service(mock_service):
    from backend.app.core.auth import CurrentUser

    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        uid="test", role="coordenacao", programa_id="prog_default", email="test@saga.edu"
    )
    app.dependency_overrides[ProgramService] = lambda: mock_service


def test_get_config_success():
    """Deve retornar 200 e os dados de configuração."""
    # Setup mock service
    mock_service = AsyncMock()
    mock_service.get_config.return_value = {"id": "prog_default", "creditos_total_min": 24}

    # Override dependencies
    from backend.app.core.auth import CurrentUser
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        uid="test", role="coordenacao", programa_id="prog_default", email="test@saga.edu"
    )
    app.dependency_overrides[ProgramService] = lambda: mock_service

    # Execute
    response = client.get("/api/v1/programs/config")
    
    # Cleanup
    app.dependency_overrides = {}

    # Assert
    assert response.status_code == 200
    assert response.json()["creditos_total_min"] == 24


def test_list_programs_success():
    """Deve retornar os programas cadastrados."""
    mock_service = AsyncMock()
    mock_service.list_programs.return_value = [
        {"id": "prog_mestrado_cc", "nome": "Mestrado em Ciência da Computação"},
    ]

    from backend.app.core.auth import CurrentUser
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        uid="test", role="coordenacao", programa_id="prog_default", email="test@saga.edu"
    )
    app.dependency_overrides[ProgramService] = lambda: mock_service

    response = client.get("/api/v1/programs")

    app.dependency_overrides = {}

    assert response.status_code == 200
    assert response.json() == [
        {"id": "prog_mestrado_cc", "nome": "Mestrado em Ciência da Computação"},
    ]


def test_update_config_success():
    """Deve retornar 200 ao atualizar com sucesso."""
    # Setup mock service
    mock_service = AsyncMock()
    mock_service.update_config.return_value = True

    # Override dependencies
    from backend.app.core.auth import CurrentUser
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        uid="test", role="coordenacao", programa_id="prog_default", email="test@saga.edu"
    )
    app.dependency_overrides[ProgramService] = lambda: mock_service

    # Execute
    response = client.put("/api/v1/programs/config", json={"creditos_total_min": 30})
    
    # Cleanup
    app.dependency_overrides = {}

    # Assert
    assert response.status_code == 200
    assert response.json()["message"] == "Configuração atualizada com sucesso"

@pytest.mark.parametrize(
    "payload",
    [
        {"creditos_total_min": -1},
        {"creditos_total_min": None},
        {"creditos_total_min": ""},
        {"creditos_total_min": 1.5},
        {"meses_ate_qualificacao": 0},
        {"meses_ate_qualificacao": -1},
    ],
)
def test_update_config_rejects_invalid_payload(payload):
    mock_service = AsyncMock()
    _override_auth_and_service(mock_service)

    response = client.put("/api/v1/programs/config", json=payload)

    app.dependency_overrides = {}

    assert response.status_code == 422
    mock_service.update_config.assert_not_called()
