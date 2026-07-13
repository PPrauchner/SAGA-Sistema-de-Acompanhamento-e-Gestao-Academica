"""
Testes para os endpoints da API de Veículos.

Responsabilidades:
- Verificar as atualizações de níveis de relevância de veículos.
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
from backend.app.services.vehicle_service import VehicleService

client = TestClient(app)


def test_update_vehicle_level_success():
    """Deve retornar 200 ao atualizar o nível do veículo com sucesso."""
    # Setup mock service
    mock_service = AsyncMock()
    mock_service.update_vehicle_level.return_value = {
        "message": "Nível de relevância atualizado",
        "peso_atribuido": 1.0,
    }

    # Override dependencies
    from backend.app.core.auth import CurrentUser
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        uid="test", role="coordenacao", programa_id="prog_default", email="test@saga.edu"
    )
    app.dependency_overrides[VehicleService] = lambda: mock_service

    # Execute
    response = client.put("/api/v1/vehicle-levels/vec_1", json={"nivel": "A1", "peso": 2.0})

    # Cleanup
    app.dependency_overrides = {}

    # Assert
    assert response.status_code == 200
    assert response.json()["message"] == "Nível de relevância atualizado"
    assert response.json()["peso_atribuido"] == 1.0
