"""
Configuração de teste para a camada de API (routers).

Responsabilidades:
- Injetar credenciais Firebase dummy nas variáveis de ambiente antes de
  backend.app.core.config ser importado, permitindo instanciar Settings sem um
  .env real.
- Neutralizar init_firebase/get_firestore_client via fixtures autouse, de modo
  que os aspectos (A02 audit) não tentem gravar no Firestore durante os testes.

Nota sobre isolamento: não se stuba `firebase_admin` em `sys.modules`. O pacote
real está instalado e `core/firebase.py` importa `credentials` e `storage` dele;
um stub parcial registrado no nível de módulo vazaria para todo o processo pytest
e quebraria a coleção das demais suítes. O isolamento é feito por `mock.patch`,
que é escopado ao teste e revertido no teardown.
"""

import os
from unittest.mock import MagicMock, patch

import pytest

os.environ.setdefault("FIREBASE_PROJECT_ID", "test-project")
os.environ.setdefault("FIREBASE_PRIVATE_KEY", "test-key")
os.environ.setdefault("FIREBASE_CLIENT_EMAIL", "test@test-project.iam.gserviceaccount.com")


@pytest.fixture(autouse=True)
def patch_firestore_client():
    """Impede que audit_operation (A02) alcance o Firestore real nos testes.

    Patcheia também `aspects.audit.get_firestore_client`: audit.py importa o nome
    no topo do módulo, então substituir só o atributo em `core.firebase` não
    intercepta a chamada — o A02 acabaria batendo no Firebase de verdade.
    """
    if os.environ.get("FIREBASE_INTEGRATION_TEST"):
        yield None
        return

    mock_db = MagicMock()
    mock_collection = MagicMock()
    mock_db.collection.return_value = mock_collection
    mock_collection.add.return_value = (None, MagicMock(id="audit_doc_test"))

    with patch("backend.app.core.firebase.get_firestore_client", return_value=mock_db), \
         patch("backend.app.aspects.audit.get_firestore_client", return_value=mock_db):
        yield mock_db


@pytest.fixture(autouse=True)
def patch_firebase_init():
    """Evita inicializar o Firebase Admin SDK real no startup da app sob teste."""
    if os.environ.get("FIREBASE_INTEGRATION_TEST"):
        yield
        return

    with patch("backend.app.core.firebase.init_firebase"), \
         patch("backend.app.core.firebase.shutdown_firebase"):
        yield
