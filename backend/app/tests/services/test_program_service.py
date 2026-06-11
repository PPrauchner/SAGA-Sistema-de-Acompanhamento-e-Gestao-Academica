"""
Tests for ProgramService.

Responsabilidades:
- Verify business logic for program configurations.
- Ensure proper interaction with the ProgramRepository.
"""

import os
from unittest.mock import MagicMock, patch

# Set dummy environment variables to satisfy pydantic-settings
os.environ["FIREBASE_PROJECT_ID"] = "test-project"
os.environ["FIREBASE_PRIVATE_KEY"] = "test-key"
os.environ["FIREBASE_CLIENT_EMAIL"] = "test-email"

import pytest
from backend.app.services.program_service import ProgramService
from backend.app.models.program_config import ProgramConfigUpdate


@pytest.fixture
def mock_repo():
    """Fixture for mocked ProgramRepository."""
    return MagicMock()


@pytest.fixture
def service(mock_repo):
    """Fixture for ProgramService with mocked repository."""
    return ProgramService(repository=mock_repo)


def test_get_config_returns_model(service, mock_repo):
    """Should fetch config from repo and return as dictionary."""
    # Setup mock
    mock_repo.get_config.return_value = {
        "id": "prog_default",
        "creditos_grupo_basico_min": 12,
        "creditos_grupo_especifico_min": 8,
        "creditos_grupo_tecnologico_max": 4,
        "creditos_total_min": 24,
        "max_prorrogacoes": 1,
        "duracao_prorrogacao_meses": 6,
        "meses_ate_qualificacao": 12
    }

    # Execute
    result = service.get_config("prog_default")

    # Assert
    assert result["creditos_total_min"] == 24
    mock_repo.get_config.assert_called_with("prog_default")


def test_update_config_calls_repo(service, mock_repo):
    """Should call repo to update config with validated data."""
    # Setup
    update_data = ProgramConfigUpdate(creditos_total_min=30)
    mock_repo.update_config.return_value = True

    # Execute
    result = service.update_config("prog_default", update_data)

    # Assert
    assert result is True
    mock_repo.update_config.assert_called_once()
    # Check that it passed the dictionary, not the model
    args, _ = mock_repo.update_config.call_args
    assert args[1] == {"creditos_total_min": 30}
