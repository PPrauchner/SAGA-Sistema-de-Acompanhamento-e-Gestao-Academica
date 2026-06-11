"""
Tests for Program API endpoints.

Responsabilidades:
- Verify GET and PUT endpoints for program configuration.
- Ensure proper integration with ProgramService.
"""

import os
from unittest.mock import MagicMock, patch

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


def test_get_config_success():
    """Should return 200 and config data."""
    # Setup mock service
    mock_service = MagicMock()
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


def test_update_config_success():
    """Should return 200 on successful update."""
    # Setup mock service
    mock_service = MagicMock()
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
