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

Exceção — testes de integração real (C2-bis):
- test_extension_integration.py precisa do firebase_admin de verdade
  (client real contra um projeto Firestore de teste), não do stub.
- Esse teste seta a variável de ambiente FIREBASE_INTEGRATION_TEST=1
  ANTES de importar backend.app.main (ver topo do próprio arquivo de
  teste). Quando essa variável está presente, _stub_firebase_modules()
  não instala o firebase_admin fake em sys.modules, permitindo que o
  import real (`from firebase_admin import auth, credentials, firestore,
  storage`) funcione normalmente dentro de backend/app/core/firebase.py.
- Sem essa variável (caso padrão dos testes unitários desta pasta), o
  comportamento é inalterado: firebase_admin continua stubado.
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
    """Instala stubs de firebase_admin antes de qualquer import da app.

    Pulado quando FIREBASE_INTEGRATION_TEST=1 está setado — nesse caso o
    firebase_admin real (já instalado via pip) deve ser usado, para que a
    suite de integração consiga se conectar a um Firestore de verdade.
    """
    if os.environ.get("FIREBASE_INTEGRATION_TEST"):
        return

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
    if os.environ.get("FIREBASE_INTEGRATION_TEST"):
        # Suite de integração: usa o Firestore real via seam de injeção
        # do próprio ExtensionRepository(client=...). Não patcheia nada.
        yield None
        return

    mock_db = MagicMock()
    mock_collection = MagicMock()
    mock_db.collection.return_value = mock_collection
    mock_collection.add.return_value = (None, MagicMock(id="audit_doc_test"))

    with patch("backend.app.core.firebase.get_firestore_client", return_value=mock_db):
        yield mock_db


@pytest.fixture(autouse=True)
def patch_firebase_init():
    if os.environ.get("FIREBASE_INTEGRATION_TEST"):
        # Suite de integração: init_firebase/shutdown_firebase reais são
        # necessários (a fixture firestore_client do teste de integração
        # inicializa sua própria app nomeada, mas o restante da aplicação
        # ainda pode chamar init_firebase() em algum ponto do startup).
        yield
        return

    with patch("backend.app.core.firebase.init_firebase"), \
         patch("backend.app.core.firebase.shutdown_firebase"):
        yield