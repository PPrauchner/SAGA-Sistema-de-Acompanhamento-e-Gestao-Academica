# backend/app/api/v1/tests/test_extension_integration.py
"""
Testes de integração para o módulo de Prorrogações de Prazo.

Pré-requisitos:
- Variáveis de ambiente FIREBASE_PROJECT_ID, FIREBASE_PRIVATE_KEY e
  FIREBASE_CLIENT_EMAIL configuradas com os dados da service account do
  projeto de teste (as mesmas três variáveis usadas em produção/dev — ver
  backend/app/core/firebase.py:_build_credentials). Não usa mais um JSON
  único via FIREBASE_SERVICE_ACCOUNT_JSON, pois essa variável não existe
  no .env real do projeto (C2-bis).
- FIREBASE_INTEGRATION_TEST=1 setada NO SHELL, antes de chamar o pytest
  (não dentro deste arquivo). O conftest.py desta pasta stuba o
  firebase_admin globalmente para os testes unitários (via
  sys.modules.setdefault, no nível de módulo); pytest carrega esse
  conftest ANTES de importar este arquivo de teste, então setar a
  variável aqui dentro chegaria tarde demais. Sem essa variável no
  ambiente do processo pytest, o import `from firebase_admin import
  credentials` falha com "cannot import name 'credentials' from
  'firebase_admin' (unknown location)", pois o stub não define esse
  atributo.

Execução (Windows/PowerShell):
    $env:FIREBASE_INTEGRATION_TEST="1"
    pytest backend/app/api/v1/tests/test_extension_integration.py -v

Execução (Git Bash / Linux / macOS):
    FIREBASE_INTEGRATION_TEST=1 pytest backend/app/api/v1/tests/test_extension_integration.py -v

Isolamento:
- STUDENT_ID / ORIENTADOR_ID / COORD_ID são gerados com uuid4 a cada run e
  usados como doc_id (não apenas como uid) para students/ e users/, o que
  elimina a necessidade de auto-id + resolução nos testes e mantém
  aluno_id == STUDENT_ID nas asserções (ver nota em seed_reference_data).
- O fixture `cleanup_firestore` apaga todos os documentos criados ao final,
  independentemente de falha.
- Nunca compartilha estado entre testes de classes diferentes.
"""

from __future__ import annotations

import uuid
import pytest

from datetime import datetime, timedelta, timezone

import firebase_admin
from firebase_admin import firestore
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.core.auth import get_current_user, CurrentUser
from backend.app.core.config import settings
from backend.app.core.firebase import _build_credentials
from backend.app.api.v1.extensions import get_extension_service
from backend.app.repositories.extension_repository import ExtensionRepository
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
    Inicializa o Firebase Admin SDK com as credenciais reais do projeto
    (mesmas três variáveis usadas em produção/dev: FIREBASE_PROJECT_ID,
    FIREBASE_PRIVATE_KEY, FIREBASE_CLIENT_EMAIL — ver
    backend/app/core/firebase.py:_build_credentials).

    Usa um app nomeado para não colidir com a app default de
    produção/dev, e reaproveita _build_credentials() em vez de duplicar
    a lógica de montagem da credencial (incluindo o tratamento de "\\n"
    na private key).
    """
    if not (
        settings.firebase_project_id
        and settings.firebase_private_key
        and settings.firebase_client_email
    ):
        pytest.skip(
            "FIREBASE_PROJECT_ID / FIREBASE_PRIVATE_KEY / FIREBASE_CLIENT_EMAIL "
            "ausentes — pulando integração"
        )

    cred     = _build_credentials()
    app_name = f"integration-test-{uuid.uuid4().hex}"

    firebase_app = firebase_admin.initialize_app(cred, name=app_name)
    db           = firestore.client(app=firebase_app)

    yield db

    firebase_admin.delete_app(firebase_app)


@pytest.fixture
def cleanup_firestore(firestore_client):
    """
    Registra paths (collection_path, doc_id) criados durante o teste e os
    apaga ao final, mesmo que o teste falhe.

    collection_path aceita tanto uma coleção raiz ("students") quanto um
    path de subcoleção completo ("students/{sid}/extensions").
    """
    created: list[tuple[str, str]] = []

    def register(collection_path: str, doc_id: str):
        created.append((collection_path, doc_id))

    yield register

    for collection_path, doc_id in created:
        try:
            firestore_client.collection(collection_path).document(doc_id).delete()
        except Exception:
            pass  # melhor esforço; não mascara falha do teste


@pytest.fixture(scope="class")
def seed_reference_data(firestore_client):
    """
    Semeia os documentos de referência exigidos pelo service antes do
    fluxo de integração rodar, e os remove ao final da classe.

    IMPORTANTE sobre identidade: para manter a asserção
    `data["aluno_id"] == STUDENT_ID` válida (aluno_id no documento é o
    student_doc_id resolvido, não o uid bruto), o documento do aluno é
    criado com doc_id == STUDENT_ID e também com o campo uid == STUDENT_ID.
    Isso faz _resolve_student_doc_id(STUDENT_ID) devolver STUDENT_ID.
    O mesmo padrão é aplicado ao orientador (users/{ORIENTADOR_ID}).

    max_prorrogacoes_aprovadas=1 é proposital: depois que test_06 aprova a
    única prorrogação do fluxo, o limite já está atingido, e test_07 não
    precisa mais escrever documentos "fake" para simular esse estado.
    """
    students_ref = firestore_client.collection("students").document(STUDENT_ID)
    students_ref.set({
        "uid": STUDENT_ID,
        "orientador_id": ORIENTADOR_ID,
        "prazo_final": datetime.now(tz=timezone.utc) + timedelta(days=180),
        "situacao_registrada": "regular",
    })

    users_ref = firestore_client.collection("users").document(ORIENTADOR_ID)
    users_ref.set({"uid": ORIENTADOR_ID, "role": "orientador"})

    config_ref = firestore_client.collection("config").document("program")
    config_ref.set({
        "max_prorrogacoes_aprovadas": 1,
        "max_semestres_por_solicitacao": 2,
        "duracao_prorrogacao_meses": 6,
    })

    yield

    for ref in (students_ref, users_ref, config_ref):
        try:
            ref.delete()
        except Exception:
            pass


@pytest.fixture
def http_client(firestore_client):
    """
    TestClient com o ExtensionService real apontando para o Firestore de
    teste, via o seam de injeção do repositório (client=...).
    A autenticação ainda é sobrescrita por cada teste via dependency_overrides.
    """
    repository   = ExtensionRepository(client=firestore_client)
    real_service = ExtensionService(repository=repository)

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

@pytest.mark.usefixtures("seed_reference_data")
class TestFluxoCompletoIntegracao:
    """
    Testa o ciclo de vida de uma prorrogação contra o Firestore real.

    Ordem dos testes é intencional: cada um depende do estado gravado
    pelo anterior. O `extension_id` é compartilhado via atributo de classe
    para evitar fixtures de sessão com estado mutável.
    """

    extension_id: str | None = None  # preenchido em test_01

    # ------------------------------------------------------------------
    # Passo 1 — Aluno cria prorrogação
    # ------------------------------------------------------------------

    def test_01_aluno_cria_prorrogacao(self, http_client, cleanup_firestore):
        app.dependency_overrides[get_current_user] = _auth("aluno", STUDENT_ID)

        response = http_client.post(
            "/api/v1/extensions",
            json=PAYLOAD_VALIDO,
        )

        assert response.status_code == 201, response.text
        data = response.json()

        assert data["status"] == ExtensionStatus.PENDENTE
        assert data["aluno_id"] == STUDENT_ID
        assert data["semestres_solicitados"] == 1

        TestFluxoCompletoIntegracao.extension_id = data["id"]
        # Doc real vive na subcoleção students/{STUDENT_ID}/extensions
        cleanup_firestore(f"students/{STUDENT_ID}/extensions", data["id"])

    # ------------------------------------------------------------------
    # Passo 2 — Segunda solicitação pendente é bloqueada
    # ------------------------------------------------------------------

    def test_02_segunda_pendente_bloqueada(self, http_client):
        app.dependency_overrides[get_current_user] = _auth("aluno", STUDENT_ID)

        response = http_client.post(
            "/api/v1/extensions",
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

        response = http_client.patch(
            f"/api/v1/extensions/{STUDENT_ID}/{self.extension_id}/review",
            json={"parecer_orientador": "Aluno demonstra progresso consistente. Recomendo aprovação."},
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

        response = http_client.patch(
            f"/api/v1/extensions/{STUDENT_ID}/{self.extension_id}/review",
            json={"parecer_orientador": "Tentativa indevida de parecer, com texto suficiente."},
        )

        assert response.status_code == 403

    # ------------------------------------------------------------------
    # Passo 5 — Aluno não pode deliberar
    # ------------------------------------------------------------------

    def test_05_aluno_nao_pode_deliberar(self, http_client):
        assert self.extension_id, "test_01 deve ter rodado antes"
        app.dependency_overrides[get_current_user] = _auth("aluno", STUDENT_ID)

        response = http_client.patch(
            f"/api/v1/extensions/{STUDENT_ID}/{self.extension_id}/approve",
            json={"aprovado": True},
        )

        assert response.status_code == 403

    # ------------------------------------------------------------------
    # Passo 6 — Coordenação aprova
    # ------------------------------------------------------------------

    def test_06_coordenacao_aprova(self, http_client, firestore_client):
        assert self.extension_id, "test_01 deve ter rodado antes"
        app.dependency_overrides[get_current_user] = _auth("coordenacao", COORD_ID)

        response = http_client.patch(
            f"/api/v1/extensions/{STUDENT_ID}/{self.extension_id}/approve",
            json={"aprovado": True},
        )

        assert response.status_code == 200, response.text
        data = response.json()
        assert data["status"] == ExtensionStatus.APROVADA

        # Verifica diretamente no Firestore, na subcoleção correta
        doc = (
            firestore_client
            .collection("students").document(STUDENT_ID)
            .collection("extensions").document(self.extension_id)
            .get()
        )
        assert doc.exists
        doc_data = doc.to_dict()
        assert doc_data["status"] == ExtensionStatus.APROVADA.value
        assert doc_data["aprovado_por"] == COORD_ID

    # ------------------------------------------------------------------
    # Passo 7 — Nova solicitação bloqueada após atingir limite aprovadas
    # ------------------------------------------------------------------

    def test_07_limite_aprovadas_bloqueado(self, http_client):
        """
        max_prorrogacoes_aprovadas=1 (seed) + a aprovação do test_06 já
        atinge o limite. Não há pendente em aberto (test_06 aprovou a
        única existente), então o 400 aqui vem do _check_limit, não do
        _check_no_pending — é isso que a asserção de mensagem confirma.
        """
        app.dependency_overrides[get_current_user] = _auth("aluno", STUDENT_ID)

        response = http_client.post(
            "/api/v1/extensions",
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

        response = http_client.get(f"/api/v1/extensions/students/{STUDENT_ID}")

        assert response.status_code == 200, response.text
        extensions = response.json()

        ids = [e["id"] for e in extensions]
        assert self.extension_id in ids

        aprovada = next(e for e in extensions if e["id"] == self.extension_id)
        assert aprovada["status"] == ExtensionStatus.APROVADA