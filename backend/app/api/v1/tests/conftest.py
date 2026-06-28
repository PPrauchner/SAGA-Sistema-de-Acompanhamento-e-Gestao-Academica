from __future__ import annotations

"""
Fixtures de infraestrutura para a suite de testes do módulo extensions.

Estratégia de isolamento:
- Firebase Admin SDK é patcheado ANTES de qualquer import da app, via
  autouse no nível de session. Isso resolve D1: main.py importa módulos
  que inicializam clientes Firebase no nível de módulo.
- get_firestore_client é patcheado para retornar um MagicMock, impedindo
  que audit_operation tente gravar no Firestore real em testes (D3).
- Os patches são aplicados via pytest fixtures com autouse=True para
  garantir que o ambiente está limpo antes de qualquer coleta.
"""

import os
import sys
from types import ModuleType
from unittest.mock import MagicMock, patch

import pytest

os.environ.setdefault("FIREBASE_PROJECT_ID", "test-project")
os.environ.setdefault("FIREBASE_PRIVATE_KEY", "test-key")
os.environ.setdefault("FIREBASE_CLIENT_EMAIL", "test@test-project.iam.gserviceaccount.com")


def _stub_firebase_modules() -> None:
    """Instala stubs de firebase_admin antes de qualquer import da app."""
    firebase_admin = ModuleType("firebase_admin")
    firebase_admin.initialize_app = MagicMock()
    firebase_admin.get_app = MagicMock()
    firebase_admin.delete_app = MagicMock()

    firebase_auth = ModuleType("firebase_admin.auth")
    firebase_auth.verify_id_token = MagicMock()

    firebase_exceptions = ModuleType("firebase_admin.exceptions")
    firebase_exceptions.FirebaseError = Exception

    firebase_firestore = ModuleType("firebase_admin.firestore")
    mock_db = MagicMock()
    mock_collection = MagicMock()
    mock_db.collection.return_value = mock_collection
    mock_collection.add.return_value = (None, MagicMock(id="audit_doc_001"))
    firebase_firestore.client = MagicMock(return_value=mock_db)

    sys.modules.setdefault("firebase_admin", firebase_admin)
    sys.modules.setdefault("firebase_admin.auth", firebase_auth)
    sys.modules.setdefault("firebase_admin.exceptions", firebase_exceptions)
    sys.modules.setdefault("firebase_admin.firestore", firebase_firestore)


_stub_firebase_modules()


@pytest.fixture(autouse=True)
def patch_firestore_client():
    mock_db = MagicMock()
    mock_collection = MagicMock()
    mock_db.collection.return_value = mock_collection
    mock_collection.add.return_value = (None, MagicMock(id="audit_doc_test"))

    with patch("backend.app.core.firebase.get_firestore_client", return_value=mock_db):
        yield mock_db


@pytest.fixture(autouse=True)
def patch_firebase_init():
    with patch("backend.app.core.firebase.init_firebase"), \
         patch("backend.app.core.firebase.shutdown_firebase"):
        yield