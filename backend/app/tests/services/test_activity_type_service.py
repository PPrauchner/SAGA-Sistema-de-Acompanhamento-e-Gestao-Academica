"""
Tests for ActivityTypeService.

Responsabilidades:
- Verify business logic for activity types management.
- Ensure proper interaction with the ActivityTypeRepository.
"""

import os
from unittest.mock import MagicMock, patch

# Set dummy environment variables to satisfy pydantic-settings
os.environ["FIREBASE_PROJECT_ID"] = "test-project"
os.environ["FIREBASE_PRIVATE_KEY"] = "test-key"
os.environ["FIREBASE_CLIENT_EMAIL"] = "test-email"

import pytest
from backend.app.services.activity_type_service import ActivityTypeService
from backend.app.models.activity_type import ActivityTypeCreate, ActivityTypeUpdate


@pytest.fixture
def mock_repo():
    """Fixture for mocked ActivityTypeRepository."""
    return MagicMock()


@pytest.fixture
def service(mock_repo):
    """Fixture for ActivityTypeService with mocked repository."""
    return ActivityTypeService(repository=mock_repo)


def test_get_all_by_program(service, mock_repo):
    """Should fetch activity types from repo."""
    # Setup mock
    mock_repo.get_all_by_program.return_value = [{"id": "1", "nome": "Artigo"}]

    # Execute
    result = service.get_all_by_program("prog_default")

    # Assert
    assert len(result) == 1
    assert result[0]["nome"] == "Artigo"
    mock_repo.get_all_by_program.assert_called_with("prog_default")


def test_create_type_calls_repo(service, mock_repo):
    """Should call repo to create activity type."""
    # Setup
    data = ActivityTypeCreate(
        nome="Patente", 
        categoria="tecnologico", 
        pontuacao_base=5.0, 
        programa_id="prog_default"
    )
    mock_repo.create_type.return_value = "new_id"

    # Execute
    result = service.create_type(data)

    # Assert
    assert result == "new_id"
    mock_repo.create_type.assert_called_once()


def test_toggle_active_switches_status(service, mock_repo):
    """Should fetch current status and toggle it."""
    # Setup
    mock_repo.get_type.return_value = {"id": "1", "ativo": True}
    mock_repo.update_type.return_value = True

    # Execute
    result = service.toggle_active("1")

    # Assert
    assert result is True
    mock_repo.update_type.assert_called_with("1", {"ativo": False})
