"""
Tests for Activity Types API endpoints.

Responsabilidades:
- Verify CRUD operations and toggling for activity types.
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
from backend.app.services.activity_type_service import ActivityTypeService

client = TestClient(app)


def test_get_activity_types_success():
    """Deve retornar 200 e a lista de tipos de atividade."""
    # Setup mock service
    mock_service = AsyncMock()
    mock_service.get_all_by_program.return_value = [{"id": "1", "nome": "Artigo", "categoria": "tecnologico", "pontuacao_base": 5.0}]

    # Override dependencies
    from backend.app.core.auth import CurrentUser
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        uid="test", role="coordenacao", programa_id="prog_default", email="test@saga.edu"
    )
    app.dependency_overrides[ActivityTypeService] = lambda: mock_service

    # Execute
    response = client.get("/api/v1/activity-types")
    
    # Cleanup
    app.dependency_overrides = {}

    # Assert
    assert response.status_code == 200
    assert len(response.json()) == 1


def test_create_activity_type_success():
    """Deve retornar 201 ao criar com sucesso."""
    # Setup mock service
    mock_service = AsyncMock()
    mock_service.create_type.return_value = "new_id"

    # Override dependencies
    from backend.app.core.auth import CurrentUser
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        uid="test", role="coordenacao", programa_id="prog_default", email="test@saga.edu"
    )
    app.dependency_overrides[ActivityTypeService] = lambda: mock_service

    # Execute
    response = client.post("/api/v1/activity-types", json={
        "nome": "Patente", 
        "categoria": "tecnologico", 
        "pontuacao_base": 5.0, 
        "programa_id": "prog_default"
    })
    
    # Cleanup
    app.dependency_overrides = {}

    # Assert
    assert response.status_code == 201
    assert response.json()["id"] == "new_id"
