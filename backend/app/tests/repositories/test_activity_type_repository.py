"""
Tests for ActivityTypeRepository.

Responsabilidades:
- Verify CRUD operations for activity types in Firestore.
"""

import os
from unittest.mock import MagicMock, patch

# Set dummy environment variables to satisfy pydantic-settings
os.environ["FIREBASE_PROJECT_ID"] = "test-project"
os.environ["FIREBASE_PRIVATE_KEY"] = "test-key"
os.environ["FIREBASE_CLIENT_EMAIL"] = "test-email"

import pytest
from backend.app.repositories.activity_type_repository import ActivityTypeRepository


@pytest.fixture
def mock_db():
    """Fixture for mocked Firestore client."""
    return MagicMock()


@pytest.fixture
def repo(mock_db):
    """Fixture for ActivityTypeRepository with mocked DB."""
    with patch("backend.app.repositories.firebase_repository.get_firestore_client", return_value=mock_db):
        return ActivityTypeRepository()


def test_get_all_by_program(repo, mock_db):
    """Should call Firestore to get activity types for a program."""
    # Setup mock
    mock_doc = MagicMock()
    mock_doc.id = "type_1"
    mock_doc.to_dict.return_value = {"nome": "Artigo", "programa_id": "prog_default"}
    mock_db.collection.return_value.where.return_value.stream.return_value = [mock_doc]

    # Execute
    result = repo.get_all_by_program("prog_default")

    # Assert
    assert len(result) == 1
    assert result[0]["id"] == "type_1"
    mock_db.collection.assert_called_with("activity_types")
    mock_db.collection.return_value.where.assert_called_with("programa_id", "==", "prog_default")
