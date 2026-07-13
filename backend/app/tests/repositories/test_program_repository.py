"""
Tests for ProgramRepository.

Responsabilidades:
- Verify CRUD operations for program configurations in Firestore.
- Verify vehicle level management within a program.
"""

import os
from unittest.mock import MagicMock, patch

# Set dummy environment variables to satisfy pydantic-settings
os.environ["FIREBASE_PROJECT_ID"] = "test-project"
os.environ["FIREBASE_PRIVATE_KEY"] = "test-key"
os.environ["FIREBASE_CLIENT_EMAIL"] = "test-email"

import pytest
from backend.app.repositories.program_repository import ProgramRepository


@pytest.fixture
def mock_db():
    """Fixture for mocked Firestore client."""
    return MagicMock()


@pytest.fixture
def repo(mock_db):
    """Fixture for ProgramRepository with mocked DB."""
    with patch("backend.app.repositories.firebase_repository.get_firestore_client", return_value=mock_db):
        yield ProgramRepository()


@pytest.fixture
def anyio_backend():
    return 'asyncio'

@pytest.mark.anyio
async def test_get_config_calls_firestore(repo, mock_db):
    """Should call Firestore to get a program document."""
    # Setup mock
    mock_doc = MagicMock()
    mock_doc.exists = True
    mock_doc.to_dict.return_value = {"creditos_total_min": 24}
    mock_db.collection.return_value.document.return_value.get.return_value = mock_doc

    # Execute
    result = await repo.get_config("prog_default")

    # Assert
    assert result["creditos_total_min"] == 24
    mock_db.collection.assert_called_with("programs")
    mock_db.collection.return_value.document.assert_called_with("prog_default")
