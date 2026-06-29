# backend/app/api/v1/tests/test_extension_integration.py
"""
Testes de integração para o módulo de Prorrogações de Prazo.

Pré-requisitos:
- Variável FIREBASE_SERVICE_ACCOUNT_JSON com o JSON da service account do
  projeto de teste (inline, não como caminho de arquivo).
- O projeto de teste deve ter uma coleção `extensions` no Firestore.

Execução:
    pytest backend/app/api/v1/tests/test_extension_integration.py -v

Isolamento:
- Cada teste cria seus próprios documentos com IDs únicos (uuid4).
- O fixture `cleanup_firestore` apaga todos os documentos criados ao final,
  independentemente de falha.
- Nunca compartilha estado entre testes.
"""

from __future__ import annotations

import json
import os
import uuid
import pytest
import pytest_asyncio

from datetime import datetime, timezone
from fastapi.testclient import TestClient

import firebase_admin
from firebase_admin import credentials, firestore

from backend.app.main import app
from backend.app.core.auth import get_current_user, CurrentUser
from backend.app.api.v1.extensions import get_extension_service
from backend.app.services.extension_service import ExtensionService
from backend.app.models.extension import ExtensionStatus

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

STUDENT_ID    = f"integ_student_{uuid.uuid4().hex[:8]}"
ORIENTADOR_ID = f"integ_advisor_{uuid.uuid4().hex[:8]}"
COORD_ID      = f"integ_coord_{uuid.uuid4().hex[:8]}"

PAYLOAD_VALIDO = {
    "motivo": "Motivo longo o suficiente para passar na validacao do modelo Pydantic",
    "plano_atualizado": "http://plano-atualizado.com/doc.pdf",
    "semestres_solicitados": 1,
}

# ---------------------------------------------------------------------------
# Fixtures de infraestrutura
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def firestore_client():
    """
    Inicializa o Firebase Admin SDK com a service account inline.
    Usa um app nomeado para não colidir com eventuais outras inicializações.
    """
    raw = os.environ.get("FIREBASE_SERVICE_ACCOUNT_JSON")
    if not raw:
        pytest.skip("FIREBASE_SERVICE_ACCOUNT_JSON não definida — pulando integração")

    sa_info = json.loads(raw)
    cred     = credentials.Certificate(sa_info)
    app_name = f"integration-test-{uuid.uuid4().hex}"

    firebase_app = firebase_admin.initialize_app(cred, name=app_name)
    db           = firestore.client(app=firebase_app)

    yield db

    firebase_admin.delete_app(firebase_app)


@pytest.fixture
def cleanup_firestore(firestore_client):
    """
    Registra IDs de documentos criados durante o teste e os apaga ao final,
    mesmo que o teste falhe.
    """
    created: list[tuple[str, str]] = []  # [(collection, doc_id), ...]

    def register(collection: str, doc_id: str):
        created.append((collection, doc_id))

    yield register

    for collection, doc_id in created:
        try:
            firestore_client.collection(collection).document(doc_id).delete()
        except Exception:
            pass  # melhor esforço; não mascara falha do teste


@pytest.fixture
def http_client(firestore_client):
    """
    TestClient com o ExtensionService real apontando para o Firestore de teste.
    A autenticação ainda é sobrescrita por cada teste via dependency_overrides.
    """
    real_service = ExtensionService(db=firestore_client)

    app.dependency_overrides[get_extension_service] = lambda: real_service
    client = TestClient(app, raise_server_exceptions=False)

    yield client

    app.dependency_overrides.clear()


def _auth(role: str, uid: str):
    """Retorna um override de get_current_user para o papel/uid dado."""
    def _override():
        return CurrentUser(uid=uid, role=role, programa_id="prog_integ")
    return _override


# ---------------------------------------------------------------------------
# Fluxo completo: criar → revisar → deliberar
# ---------------------------------------------------------------------------

class TestFluxoCompletoIntegracao:
    """
    Testa o ciclo de vida de uma prorrogação contra o Firestore real.

    Ordem dos testes é intencional: cada um depende do estado gravado
    pelo anterior.  O `extension_id` é compartilhado via atributo de classe
    para evitar fixtures de sessão com estado mutável.
    """

    extension_id: str | None = None  # preenchido em test_01

    # ------------------------------------------------------------------
    # Passo 1 — Aluno cria prorrogação
    # ------------------------------------------------------------------

    def test_01_aluno_cria_prorrogacao(self, http_client, cleanup_firestore):
        app.dependency_overrides[get_current_user] = _auth("aluno", STUDENT_ID)

        response = http_client.post(
            f"/api/v1/extensions",
            json=PAYLOAD_VALIDO,
        )

        assert response.status_code == 201, response.text
        data = response.json()

        assert data["status"] == ExtensionStatus.PENDENTE
        assert data["student_id"] == STUDENT_ID
        assert data["semestres_solicitados"] == 1

        # Registra para limpeza e compartilha com passos seguintes
        TestFluxoCompletoIntegracao.extension_id = data["id"]
        cleanup_firestore("extensions", data["id"])

    # ------------------------------------------------------------------
    # Passo 2 — Segunda solicitação pendente é bloqueada
    # ------------------------------------------------------------------

    def test_02_segunda_pendente_bloqueada(self, http_client):
        app.dependency_overrides[get_current_user] = _auth("aluno", STUDENT_ID)

        response = http_client.post(
            f"/api/v1/extensions",
            json=PAYLOAD_VALIDO,
        )

        assert response.status_code == 400
        assert "pendente" in response.json()["detail"].lower()

    # ------------------------------------------------------------------
    # Passo 3 — Orientador adiciona parecer
    # ------------------------------------------------------------------

    def test_03_orientador_adiciona_parecer(self, http_client):
        assert self.extension_id, "test_01 deve ter rodado antes"
        app.dependency_overrides[get_current_user] = _auth("orientador", ORIENTADOR_ID)

        response = http_client.post(
            f"/api/v1/extensions/{STUDENT_ID}/{self.extension_id}/review",
            json={"parecer": "Aluno demonstra progresso consistente. Recomendo aprovação."},
        )

        assert response.status_code == 200, response.text
        data = response.json()
        # Após parecer do orientador o status ainda é PENDENTE (aguarda coord)
        assert data["status"] == ExtensionStatus.PENDENTE

    # ------------------------------------------------------------------
    # Passo 4 — Orientador errado não pode adicionar segundo parecer
    # ------------------------------------------------------------------

    def test_04_orientador_intruso_bloqueado(self, http_client):
        assert self.extension_id, "test_01 deve ter rodado antes"
        app.dependency_overrides[get_current_user] = _auth(
            "orientador", f"intruso_{uuid.uuid4().hex[:6]}"
        )

        response = http_client.post(
            f"/api/v1/extensions/{STUDENT_ID}/{self.extension_id}/review",
            json={"parecer": "Tentativa indevida de parecer."},
        )

        assert response.status_code == 403

    # ------------------------------------------------------------------
    # Passo 5 — Aluno não pode deliberar
    # ------------------------------------------------------------------

    def test_05_aluno_nao_pode_deliberar(self, http_client):
        assert self.extension_id, "test_01 deve ter rodado antes"
        app.dependency_overrides[get_current_user] = _auth("aluno", STUDENT_ID)

        response = http_client.post(
            f"/api/v1/extensions/{STUDENT_ID}/{self.extension_id}/decision",
            json={"decisao": "aprovada", "justificativa": "Tentativa indevida."},
        )

        assert response.status_code == 403

    # ------------------------------------------------------------------
    # Passo 6 — Coordenação aprova
    # ------------------------------------------------------------------

    def test_06_coordenacao_aprova(self, http_client, firestore_client):
        assert self.extension_id, "test_01 deve ter rodado antes"
        app.dependency_overrides[get_current_user] = _auth("coordenacao", COORD_ID)

        response = http_client.post(
            f"/api/v1/extensions/{STUDENT_ID}/{self.extension_id}/decision",
            json={
                "decisao": "aprovada",
                "justificativa": "Documentação completa e parecer positivo do orientador.",
            },
        )

        assert response.status_code == 200, response.text
        data = response.json()
        assert data["status"] == ExtensionStatus.APROVADA

        # Verifica diretamente no Firestore que o documento foi atualizado
        doc = (
            firestore_client
            .collection("extensions")
            .document(self.extension_id)
            .get()
        )
        assert doc.exists
        assert doc.to_dict()["status"] == ExtensionStatus.APROVADA
        assert doc.to_dict()["deliberado_por"] == COORD_ID

    # ------------------------------------------------------------------
    # Passo 7 — Nova solicitação bloqueada após atingir limite aprovadas
    # ------------------------------------------------------------------

    def test_07_limite_aprovadas_bloqueado(self, http_client, cleanup_firestore):
        """
        Após atingir o limite de prorrogações aprovadas, uma nova tentativa
        deve retornar 400.

        Este teste cria uma segunda prorrogação aprovada diretamente no
        Firestore para simular o estado de limite atingido, sem precisar
        repetir o fluxo completo.
        """
        # Insere uma segunda aprovação manualmente para forçar o limite
        doc_ref = (
            firestore_client
            .collection("extensions")
            .document()
        )
        doc_ref.set({
            "student_id": STUDENT_ID,
            "status": ExtensionStatus.APROVADA,
            "semestres_solicitados": 1,
            "criado_em": datetime.now(tz=timezone.utc),
        })
        cleanup_firestore("extensions", doc_ref.id)

        app.dependency_overrides[get_current_user] = _auth("aluno", STUDENT_ID)
        response = http_client.post(
            f"/api/v1/extensions",
            json=PAYLOAD_VALIDO,
        )

        assert response.status_code == 400
        assert "limite" in response.json()["detail"].lower()

    # ------------------------------------------------------------------
    # Passo 8 — Consulta de histórico do aluno reflete estado real
    # ------------------------------------------------------------------

    def test_08_historico_aluno_contem_prorrogacao_aprovada(self, http_client):
        assert self.extension_id, "test_01 deve ter rodado antes"
        app.dependency_overrides[get_current_user] = _auth("aluno", STUDENT_ID)

        response = http_client.get(f"/api/v1/extensions/{STUDENT_ID}")

        assert response.status_code == 200, response.text
        extensions = response.json()

        ids = [e["id"] for e in extensions]
        assert self.extension_id in ids

        aprovada = next(e for e in extensions if e["id"] == self.extension_id)
        assert aprovada["status"] == ExtensionStatus.APROVADA