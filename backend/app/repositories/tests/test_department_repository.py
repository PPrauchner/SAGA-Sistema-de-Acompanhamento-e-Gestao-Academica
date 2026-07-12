"""
Testes para DepartmentRepository — especificamente has_programs, usado para bloquear
a exclusão de departamentos com programas vinculados (ADR-0004).
"""

import os
from unittest.mock import MagicMock, patch

os.environ["FIREBASE_PROJECT_ID"] = "test-project"
os.environ["FIREBASE_PRIVATE_KEY"] = "test-key"
os.environ["FIREBASE_CLIENT_EMAIL"] = "test-email"

import pytest

from backend.app.repositories.department_repository import DepartmentRepository


@pytest.fixture
def mock_db():
    return MagicMock()


@pytest.fixture
def repo(mock_db):
    with patch(
        "backend.app.repositories.firebase_repository.get_firestore_client",
        return_value=mock_db,
    ):
        yield DepartmentRepository()


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_has_programs_true_quando_ha_programa_vinculado(repo, mock_db):
    mock_doc = MagicMock()
    mock_doc.to_dict.return_value = {"departamento_id": "dept1"}
    mock_doc.id = "prog1"
    mock_db.collection.return_value.where.return_value.limit.return_value.stream.return_value = [
        mock_doc
    ]

    assert await repo.has_programs("dept1") is True
    mock_db.collection.assert_called_with("programs")
    mock_db.collection.return_value.where.assert_called_with(
        "departamento_id", "==", "dept1"
    )


@pytest.mark.anyio
async def test_has_programs_false_quando_nenhum_programa_vinculado(repo, mock_db):
    mock_db.collection.return_value.where.return_value.limit.return_value.stream.return_value = []

    assert await repo.has_programs("dept1") is False
