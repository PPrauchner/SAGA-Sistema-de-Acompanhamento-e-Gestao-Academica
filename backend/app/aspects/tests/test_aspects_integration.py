"""
Testes dos aspectos AOP — sem Firebase real, sem credenciais reais.

"""

import os
import sys
import pytest
from unittest.mock import MagicMock, patch

# ---------------------------------------------------------------------------
# Mocks globais ANTES de qualquer import do projeto
# ---------------------------------------------------------------------------

_firebase_mock = MagicMock()
sys.modules.setdefault("firebase_admin", _firebase_mock)
sys.modules.setdefault("firebase_admin.credentials", MagicMock())
sys.modules.setdefault("firebase_admin.auth", MagicMock())
sys.modules.setdefault("firebase_admin.firestore", MagicMock())

# Variáveis dummy (mesmo padrão de backend/app/api/v1/tests/conftest.py) para que
# backend.app.core.config/firebase importem de verdade sem exigir um .env — nenhum
# teste aqui chama get_firestore_client() sem antes monkeypatchá-lo, então a
# credencial nunca é de fato usada. Faz-se via os.environ (setdefault, process-wide
# e idempotente) em vez de substituir sys.modules: substituir o módulo inteiro sem
# reverter deixava o mock vazar para qualquer teste que importasse `settings` pela
# primeira vez depois deste arquivo no mesmo processo pytest (regressão observada
# em test_email.py / test_auth_service.py só no full-suite).
os.environ.setdefault("FIREBASE_PROJECT_ID", "test-project")
os.environ.setdefault("FIREBASE_PRIVATE_KEY", "test-key")
os.environ.setdefault("FIREBASE_CLIENT_EMAIL", "test@test-project.iam.gserviceaccount.com")

for mod in ["backend", "backend.app", "backend.app.core"]:
    sys.modules.setdefault(mod, MagicMock())

from fastapi import HTTPException

from backend.app.core.auth import CurrentUser

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def user_coordenacao():
    return CurrentUser(uid="coord-uid-001", email="coord@saga.com", role="coordenacao", programa_id="prog-001")

@pytest.fixture
def user_orientador():
    return CurrentUser(uid="orient-uid-002", email="orient@saga.com", role="orientador", programa_id="prog-001")

@pytest.fixture
def user_aluno():
    return CurrentUser(uid="aluno-uid-003", email="aluno@saga.com", role="aluno", programa_id="prog-001")

def make_db_mock():
    db = MagicMock()
    db.collection.return_value.add = MagicMock()
    return db

def _build_alerta(activity_id, destinatario_id):
    """Helper: retorna um build callable para testes de trigger_alerts."""
    def build(result, args, kwargs):
        return {
            "tipo": "atividade_aprovada",
            "titulo": "Atividade aprovada",
            "mensagem": f"Atividade {kwargs.get('activity_id', activity_id)} aprovada.",
            "destinatario_id": destinatario_id,
        }
    return build

# ===========================================================================
# A01 — @requires_role
# ===========================================================================

class TestRequiresRole:

    @pytest.mark.asyncio
    async def test_role_permitido_executa_funcao(self, user_coordenacao):
        with patch("backend.app.aspects.aspect_config.AUTHORIZATION_ENABLED", True):
            from backend.app.aspects.authorization import requires_role

            @requires_role("coordenacao", "orientador")
            async def handler(current_user: CurrentUser):
                return "ok"

            assert await handler(current_user=user_coordenacao) == "ok"

    @pytest.mark.asyncio
    async def test_role_nao_permitido_levanta_403(self, user_aluno):
        with patch("backend.app.aspects.aspect_config.AUTHORIZATION_ENABLED", True):
            from backend.app.aspects.authorization import requires_role

            @requires_role("coordenacao")
            async def handler(current_user: CurrentUser):
                return "ok"

            with pytest.raises(HTTPException) as exc:
                await handler(current_user=user_aluno)
            assert exc.value.status_code == 403

    @pytest.mark.asyncio
    async def test_sem_current_user_levanta_401(self):
        with patch("backend.app.aspects.aspect_config.AUTHORIZATION_ENABLED", True):
            from backend.app.aspects.authorization import requires_role

            @requires_role("coordenacao")
            async def handler(current_user=None):
                return "ok"

            with pytest.raises(HTTPException) as exc:
                await handler()
            assert exc.value.status_code == 401

    @pytest.mark.asyncio
    async def test_flag_desabilitada_bypassa(self, user_aluno):
        with patch("backend.app.aspects.aspect_config.AUTHORIZATION_ENABLED", False):
            from backend.app.aspects.authorization import requires_role

            @requires_role("coordenacao")
            async def handler(current_user: CurrentUser):
                return "bypassed"

            assert await handler(current_user=user_aluno) == "bypassed"

    @pytest.mark.asyncio
    async def test_multiplos_roles_permitidos(self, user_orientador):
        with patch("backend.app.aspects.aspect_config.AUTHORIZATION_ENABLED", True):
            from backend.app.aspects.authorization import requires_role

            @requires_role("coordenacao", "orientador", "aluno")
            async def handler(current_user: CurrentUser):
                return current_user.role

            assert await handler(current_user=user_orientador) == "orientador"

# ===========================================================================
# A01 — @requires_ownership
# ===========================================================================

class TestRequiresOwnership:

    @pytest.mark.asyncio
    async def test_orientador_dono_executa(self, user_orientador):
        with patch("backend.app.aspects.aspect_config.AUTHORIZATION_ENABLED", True):
            from backend.app.aspects.authorization import requires_ownership

            @requires_ownership(lambda kw: "orient-uid-002")
            async def handler(activity_id, current_user: CurrentUser):
                return "ok"

            assert await handler(activity_id="act-1", current_user=user_orientador) == "ok"

    @pytest.mark.asyncio
    async def test_orientador_nao_dono_levanta_403(self, user_orientador):
        with patch("backend.app.aspects.aspect_config.AUTHORIZATION_ENABLED", True):
            from backend.app.aspects.authorization import requires_ownership

            @requires_ownership(lambda kw: "outro-uid")
            async def handler(activity_id, current_user: CurrentUser):
                return "ok"

            with pytest.raises(HTTPException) as exc:
                await handler(activity_id="act-1", current_user=user_orientador)
            assert exc.value.status_code == 403

    @pytest.mark.asyncio
    async def test_coordenacao_bypassa_ownership(self, user_coordenacao):
        with patch("backend.app.aspects.aspect_config.AUTHORIZATION_ENABLED", True):
            from backend.app.aspects.authorization import requires_ownership

            @requires_ownership(lambda kw: "qualquer-outro-uid")
            async def handler(activity_id, current_user: CurrentUser):
                return "coord-ok"

            assert await handler(activity_id="act-1", current_user=user_coordenacao) == "coord-ok"

    @pytest.mark.asyncio
    async def test_recurso_nao_encontrado_levanta_404(self, user_orientador):
        with patch("backend.app.aspects.aspect_config.AUTHORIZATION_ENABLED", True):
            from backend.app.aspects.authorization import requires_ownership

            @requires_ownership(lambda kw: None)
            async def handler(activity_id, current_user: CurrentUser):
                return "ok"

            with pytest.raises(HTTPException) as exc:
                await handler(activity_id="inexistente", current_user=user_orientador)
            assert exc.value.status_code == 404

    @pytest.mark.asyncio
    async def test_ownership_desabilitado_bypassa(self, user_aluno):
        with patch("backend.app.aspects.aspect_config.AUTHORIZATION_ENABLED", False):
            from backend.app.aspects.authorization import requires_ownership

            @requires_ownership(lambda kw: "outro-uid")
            async def handler(activity_id, current_user: CurrentUser):
                return "bypassed"

            assert await handler(activity_id="act-1", current_user=user_aluno) == "bypassed"

# ===========================================================================
# A02 — @audit_operation
# ===========================================================================

class TestAuditOperation:

    @pytest.mark.asyncio
    async def test_grava_log_sucesso(self, user_coordenacao):
        db = make_db_mock()
        with patch("backend.app.aspects.aspect_config.AUDIT_ENABLED", True), \
             patch("backend.app.aspects.audit.get_firestore_client", return_value=db):
            from backend.app.aspects.audit import audit_operation

            @audit_operation(operacao="aprovar_atividade", entidade="activities")
            async def handler(activity_id, current_user: CurrentUser):
                return {"status": "aprovada"}

            result = await handler(activity_id="act-123", current_user=user_coordenacao)

        assert result == {"status": "aprovada"}
        doc = db.collection.return_value.add.call_args[0][0]
        assert doc["resultado_status"] == "sucesso"
        assert doc["operacao"] == "aprovar_atividade"
        assert doc["usuario_id"] == "coord-uid-001"
        assert doc["role"] == "coordenacao"

    @pytest.mark.asyncio
    async def test_grava_log_erro_e_relanca(self, user_orientador):
        db = make_db_mock()
        with patch("backend.app.aspects.aspect_config.AUDIT_ENABLED", True), \
             patch("backend.app.aspects.audit.get_firestore_client", return_value=db):
            from backend.app.aspects.audit import audit_operation

            @audit_operation(operacao="op_falha", entidade="activities")
            async def handler(activity_id, current_user: CurrentUser):
                raise ValueError("erro simulado")

            with pytest.raises(ValueError, match="erro simulado"):
                await handler(activity_id="act-err", current_user=user_orientador)

        doc = db.collection.return_value.add.call_args[0][0]
        assert doc["resultado_status"] == "erro"
        assert "erro simulado" in doc["erro_mensagem"]

    @pytest.mark.asyncio
    async def test_desabilitado_nao_chama_firestore(self, user_coordenacao):
        db = make_db_mock()
        with patch("backend.app.aspects.aspect_config.AUDIT_ENABLED", False), \
             patch("backend.app.aspects.audit.get_firestore_client", return_value=db):
            from backend.app.aspects.audit import audit_operation

            @audit_operation(operacao="op_off", entidade="activities")
            async def handler(current_user: CurrentUser):
                return "ok"

            result = await handler(current_user=user_coordenacao)

        assert result == "ok"
        db.collection.assert_not_called()

    @pytest.mark.asyncio
    async def test_falha_firestore_nao_derruba_operacao(self, user_coordenacao):
        with patch("backend.app.aspects.aspect_config.AUDIT_ENABLED", True), \
             patch("backend.app.aspects.audit.get_firestore_client", side_effect=Exception("firestore down")):
            from backend.app.aspects.audit import audit_operation

            @audit_operation(operacao="op_resiliente", entidade="activities")
            async def handler(current_user: CurrentUser):
                return "ok"

            assert await handler(current_user=user_coordenacao) == "ok"

    @pytest.mark.asyncio
    async def test_sem_current_user_campos_sao_none(self):
        db = make_db_mock()
        with patch("backend.app.aspects.aspect_config.AUDIT_ENABLED", True), \
             patch("backend.app.aspects.audit.get_firestore_client", return_value=db):
            from backend.app.aspects.audit import audit_operation

            @audit_operation(operacao="op_anonima", entidade="activities")
            async def handler():
                return "ok"

            await handler()

        doc = db.collection.return_value.add.call_args[0][0]
        assert doc["usuario_id"] == ""

# ===========================================================================
# A05 — @trigger_alerts
# ===========================================================================

class TestTriggerAlerts:

    @pytest.mark.asyncio
    async def test_grava_notificacao_apos_execucao(self, user_coordenacao):
        db = make_db_mock()
        with patch("backend.app.aspects.aspect_config.ALERTS_ENABLED", True), \
             patch("backend.app.aspects.alerts.get_firestore_client", return_value=db):
            from backend.app.aspects.alerts import trigger_alerts

            @trigger_alerts(
                lambda result, args, kwargs: {
                    "tipo": "atividade_aprovada",
                    "titulo": "Atividade aprovada",
                    "mensagem": f"Atividade {kwargs.get('activity_id')} aprovada.",
                    "destinatario_id": "aluno-uid-003",
                }
            )
            async def handler(activity_id, current_user: CurrentUser):
                return {"novo_status": "aprovada"}

            result = await handler(activity_id="act-789", current_user=user_coordenacao)

        assert result == {"novo_status": "aprovada"}
        doc = db.collection.return_value.add.call_args[0][0]
        assert doc["tipo"] == "atividade_aprovada"
        assert "act-789" in doc["mensagem"]
        assert doc["destinatario_id"] == "aluno-uid-003"
        assert doc["lida"] is False

    @pytest.mark.asyncio
    async def test_advice_after_funcao_roda_primeiro(self, user_coordenacao):
        ordem = []
        db = make_db_mock()
        db.collection.return_value.add = lambda doc: ordem.append("alerta")

        with patch("backend.app.aspects.aspect_config.ALERTS_ENABLED", True), \
             patch("backend.app.aspects.alerts.get_firestore_client", return_value=db):
            from backend.app.aspects.alerts import trigger_alerts

            @trigger_alerts(
                lambda result, args, kwargs: {
                    "tipo": "teste_ordem",
                    "titulo": "Ordem",
                    "mensagem": "msg",
                    "destinatario_id": "aluno-uid-003",
                }
            )
            async def handler(current_user: CurrentUser):
                ordem.append("funcao")
                return "ok"

            await handler(current_user=user_coordenacao)

        assert ordem == ["funcao", "alerta"]

    @pytest.mark.asyncio
    async def test_desabilitado_nao_grava(self, user_coordenacao):
        db = make_db_mock()
        with patch("backend.app.aspects.aspect_config.ALERTS_ENABLED", False), \
             patch("backend.app.aspects.alerts.get_firestore_client", return_value=db):
            from backend.app.aspects.alerts import trigger_alerts

            @trigger_alerts(lambda result, args, kwargs: {
                "tipo": "test_off",
                "titulo": "Off",
                "mensagem": "msg",
                "destinatario_id": "aluno-uid-003",
            })
            async def handler(current_user: CurrentUser):
                return "ok"

            result = await handler(current_user=user_coordenacao)

        assert result == "ok"
        db.collection.assert_not_called()

    @pytest.mark.asyncio
    async def test_destinatario_none_nao_grava(self, user_coordenacao):
        db = make_db_mock()
        with patch("backend.app.aspects.aspect_config.ALERTS_ENABLED", True), \
             patch("backend.app.aspects.alerts.get_firestore_client", return_value=db):
            from backend.app.aspects.alerts import trigger_alerts

            @trigger_alerts(lambda result, args, kwargs: None)
            async def handler(current_user: CurrentUser):
                return "ok"

            await handler(current_user=user_coordenacao)

        db.collection.assert_not_called()

    @pytest.mark.asyncio
    async def test_erro_no_alerta_nao_derruba_operacao(self, user_coordenacao):
        with patch("backend.app.aspects.aspect_config.ALERTS_ENABLED", True), \
             patch("backend.app.aspects.alerts.get_firestore_client", side_effect=Exception("firestore down")):
            from backend.app.aspects.alerts import trigger_alerts

            @trigger_alerts(lambda result, args, kwargs: {
                "tipo": "test_resiliente",
                "titulo": "Resiliente",
                "mensagem": "msg",
                "destinatario_id": "aluno-uid-003",
            })
            async def handler(current_user: CurrentUser):
                return "ok"

            assert await handler(current_user=user_coordenacao) == "ok"

    @pytest.mark.asyncio
    async def test_disparar_alerta_prazo_qualificacao(self):
        db = make_db_mock()
        with patch("backend.app.aspects.aspect_config.ALERTS_ENABLED", True), \
             patch("backend.app.aspects.alerts.get_firestore_client", return_value=db):
            from backend.app.aspects.alerts import disparar_alerta_prazo

            await disparar_alerta_prazo(
                destinatario_id="aluno-uid-003",
                nome_aluno="João Silva",
                tipo_prazo="qualificacao",
                dias_restantes=7,
                student_id="student-001",
            )

        doc = db.collection.return_value.add.call_args[0][0]
        assert doc["tipo"] == "prazo_critico"
        assert "qualificação" in doc["mensagem"]
        assert "João Silva" in doc["mensagem"]
        assert "7" in doc["mensagem"]
        assert doc["lida"] is False

    @pytest.mark.asyncio
    async def test_disparar_alerta_prazo_final(self):
        db = make_db_mock()
        with patch("backend.app.aspects.aspect_config.ALERTS_ENABLED", True), \
             patch("backend.app.aspects.alerts.get_firestore_client", return_value=db):
            from backend.app.aspects.alerts import disparar_alerta_prazo

            await disparar_alerta_prazo(
                destinatario_id="orient-uid-002",
                nome_aluno="Maria Santos",
                tipo_prazo="final",
                dias_restantes=3,
                student_id="student-002",
            )

        doc = db.collection.return_value.add.call_args[0][0]
        assert "entrega final" in doc["mensagem"]
        assert "3" in doc["mensagem"]

    @pytest.mark.asyncio
    async def test_disparar_alerta_prazo_desabilitado(self):
        db = make_db_mock()
        with patch("backend.app.aspects.aspect_config.ALERTS_ENABLED", False), \
             patch("backend.app.aspects.alerts.get_firestore_client", return_value=db):
            from backend.app.aspects.alerts import disparar_alerta_prazo

            await disparar_alerta_prazo(
                destinatario_id="aluno-uid-003",
                nome_aluno="Teste",
                tipo_prazo="qualificacao",
                dias_restantes=5,
                student_id="student-003",
            )

        db.collection.assert_not_called()

# ===========================================================================
# Integração — stack completo dos decoradores
# ===========================================================================

class TestDecoratorStack:

    @pytest.mark.asyncio
    async def test_stack_completo_sucesso(self, user_coordenacao):
        audit_docs = []
        alert_docs = []
        db_audit = make_db_mock()
        db_alerts = make_db_mock()
        db_audit.collection.return_value.add = lambda doc: audit_docs.append(doc)
        db_alerts.collection.return_value.add = lambda doc: alert_docs.append(doc)

        with patch("backend.app.aspects.aspect_config.AUTHORIZATION_ENABLED", True), \
             patch("backend.app.aspects.aspect_config.AUDIT_ENABLED", True), \
             patch("backend.app.aspects.aspect_config.ALERTS_ENABLED", True), \
             patch("backend.app.aspects.audit.get_firestore_client", return_value=db_audit), \
             patch("backend.app.aspects.alerts.get_firestore_client", return_value=db_alerts):

            from backend.app.aspects.authorization import requires_role
            from backend.app.aspects.audit import audit_operation
            from backend.app.aspects.alerts import trigger_alerts

            @requires_role("coordenacao")
            @audit_operation(operacao="aprovar_stack", entidade="activities")
            @trigger_alerts(
                lambda result, args, kwargs: {
                    "tipo": "aprovacao_stack",
                    "titulo": "Aprovado",
                    "mensagem": f"Aprovado: {kwargs.get('activity_id')}",
                    "destinatario_id": "aluno-uid-003",
                }
            )
            async def validate_activity(activity_id, current_user: CurrentUser):
                return {"novo_status": "aprovada", "creditos": 10}

            result = await validate_activity(activity_id="act-stack-001", current_user=user_coordenacao)

        assert result["novo_status"] == "aprovada"
        assert len(audit_docs) == 1
        assert audit_docs[0]["resultado_status"] == "sucesso"
        assert len(alert_docs) == 1

    @pytest.mark.asyncio
    async def test_role_negado_nao_executa_audit_nem_alerta(self, user_aluno):
        db = make_db_mock()

        with patch("backend.app.aspects.aspect_config.AUTHORIZATION_ENABLED", True), \
             patch("backend.app.aspects.aspect_config.AUDIT_ENABLED", True), \
             patch("backend.app.aspects.aspect_config.ALERTS_ENABLED", True), \
             patch("backend.app.aspects.audit.get_firestore_client", return_value=db), \
             patch("backend.app.aspects.alerts.get_firestore_client", return_value=db):

            from backend.app.aspects.authorization import requires_role
            from backend.app.aspects.audit import audit_operation
            from backend.app.aspects.alerts import trigger_alerts

            @requires_role("coordenacao")
            @audit_operation(operacao="bloqueada", entidade="activities")
            @trigger_alerts(lambda result, args, kwargs: {
                "tipo": "bloqueada",
                "titulo": "Nunca",
                "mensagem": "msg",
                "destinatario_id": "aluno-uid-003",
            })
            async def validate_activity(activity_id, current_user: CurrentUser):
                return "nunca executa"

            with pytest.raises(HTTPException) as exc:
                await validate_activity(activity_id="act-block", current_user=user_aluno)

        assert exc.value.status_code == 403
        db.collection.assert_not_called()

    @pytest.mark.asyncio
    async def test_excecao_na_func_grava_audit_erro_sem_alerta(self, user_coordenacao):
        audit_docs = []
        alert_docs = []
        db_audit = make_db_mock()
        db_alerts = make_db_mock()
        db_audit.collection.return_value.add = lambda doc: audit_docs.append(doc)
        db_alerts.collection.return_value.add = lambda doc: alert_docs.append(doc)

        with patch("backend.app.aspects.aspect_config.AUTHORIZATION_ENABLED", True), \
             patch("backend.app.aspects.aspect_config.AUDIT_ENABLED", True), \
             patch("backend.app.aspects.aspect_config.ALERTS_ENABLED", True), \
             patch("backend.app.aspects.audit.get_firestore_client", return_value=db_audit), \
             patch("backend.app.aspects.alerts.get_firestore_client", return_value=db_alerts):

            from backend.app.aspects.authorization import requires_role
            from backend.app.aspects.audit import audit_operation
            from backend.app.aspects.alerts import trigger_alerts

            @requires_role("coordenacao")
            @audit_operation(operacao="op_com_erro", entidade="activities")
            @trigger_alerts(lambda result, args, kwargs: {
                "tipo": "nunca_dispara",
                "titulo": "Nunca",
                "mensagem": "msg",
                "destinatario_id": "aluno-uid-003",
            })
            async def validate_activity(activity_id, current_user: CurrentUser):
                raise ValueError("erro de negócio")

            with pytest.raises(ValueError):
                await validate_activity(activity_id="act-err", current_user=user_coordenacao)

        assert len(audit_docs) == 1
        assert audit_docs[0]["resultado_status"] == "erro"
        assert len(alert_docs) == 0