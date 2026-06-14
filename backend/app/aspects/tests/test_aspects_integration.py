"""
Testes dos aspectos AOP — sem Firebase, sem credenciais, tudo mockado.

"""

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

_pydantic_settings = MagicMock()
_pydantic_settings.BaseSettings = object
_pydantic_settings.SettingsConfigDict = dict
sys.modules.setdefault("pydantic_settings", _pydantic_settings)

_settings_mock = MagicMock()
_settings_mock.deadline_alert_days = 30
_settings_mock.max_extensions = 2
_config_mock = MagicMock()
_config_mock.settings = _settings_mock

for mod in ["backend", "backend.app", "backend.app.core"]:
    sys.modules.setdefault(mod, MagicMock())
sys.modules["backend.app.core.config"] = _config_mock
sys.modules["backend.app.core.firebase"] = MagicMock()

from fastapi import HTTPException

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def user_coordenacao():
    return {"uid": "coord-uid-001", "email": "coord@saga.com", "role": "coordenacao"}

@pytest.fixture
def user_orientador():
    return {"uid": "orient-uid-002", "email": "orient@saga.com", "role": "orientador"}

@pytest.fixture
def user_aluno():
    return {"uid": "aluno-uid-003", "email": "aluno@saga.com", "role": "aluno"}

def make_db_mock():
    db = MagicMock()
    db.collection.return_value.add = MagicMock()
    return db

# ===========================================================================
# A01 — @requires_role
# ===========================================================================

class TestRequiresRole:

    @pytest.mark.asyncio
    async def test_role_permitido_executa_funcao(self, user_coordenacao):
        with patch("backend.app.aspects.aspect_config.AUTHORIZATION_ENABLED", True):
            from backend.app.aspects.authorization import requires_role

            @requires_role("coordenacao", "orientador")
            async def handler(current_user):
                return "ok"

            assert await handler(current_user=user_coordenacao) == "ok"

    @pytest.mark.asyncio
    async def test_role_nao_permitido_levanta_403(self, user_aluno):
        with patch("backend.app.aspects.aspect_config.AUTHORIZATION_ENABLED", True):
            from backend.app.aspects.authorization import requires_role

            @requires_role("coordenacao")
            async def handler(current_user):
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
            async def handler(current_user):
                return "bypassed"

            assert await handler(current_user=user_aluno) == "bypassed"

    @pytest.mark.asyncio
    async def test_multiplos_roles_permitidos(self, user_orientador):
        with patch("backend.app.aspects.aspect_config.AUTHORIZATION_ENABLED", True):
            from backend.app.aspects.authorization import requires_role

            @requires_role("coordenacao", "orientador", "aluno")
            async def handler(current_user):
                return current_user["role"]

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
            async def handler(activity_id, current_user):
                return "ok"

            assert await handler(activity_id="act-1", current_user=user_orientador) == "ok"

    @pytest.mark.asyncio
    async def test_orientador_nao_dono_levanta_403(self, user_orientador):
        with patch("backend.app.aspects.aspect_config.AUTHORIZATION_ENABLED", True):
            from backend.app.aspects.authorization import requires_ownership

            @requires_ownership(lambda kw: "outro-uid")
            async def handler(activity_id, current_user):
                return "ok"

            with pytest.raises(HTTPException) as exc:
                await handler(activity_id="act-1", current_user=user_orientador)
            assert exc.value.status_code == 403

    @pytest.mark.asyncio
    async def test_coordenacao_bypassa_ownership(self, user_coordenacao):
        with patch("backend.app.aspects.aspect_config.AUTHORIZATION_ENABLED", True):
            from backend.app.aspects.authorization import requires_ownership

            @requires_ownership(lambda kw: "qualquer-outro-uid")
            async def handler(activity_id, current_user):
                return "coord-ok"

            assert await handler(activity_id="act-1", current_user=user_coordenacao) == "coord-ok"

    @pytest.mark.asyncio
    async def test_recurso_nao_encontrado_levanta_404(self, user_orientador):
        with patch("backend.app.aspects.aspect_config.AUTHORIZATION_ENABLED", True):
            from backend.app.aspects.authorization import requires_ownership

            @requires_ownership(lambda kw: None)
            async def handler(activity_id, current_user):
                return "ok"

            with pytest.raises(HTTPException) as exc:
                await handler(activity_id="inexistente", current_user=user_orientador)
            assert exc.value.status_code == 404

    @pytest.mark.asyncio
    async def test_ownership_desabilitado_bypassa(self, user_aluno):
        with patch("backend.app.aspects.aspect_config.AUTHORIZATION_ENABLED", False):
            from backend.app.aspects.authorization import requires_ownership

            @requires_ownership(lambda kw: "outro-uid")
            async def handler(activity_id, current_user):
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

            @audit_operation(
                operacao="aprovar_atividade",
                entidade="activities",
                get_entity_id_fn=lambda kw: kw.get("activity_id"),
            )
            async def handler(activity_id, current_user):
                return {"status": "aprovada"}

            result = await handler(activity_id="act-123", current_user=user_coordenacao)

        assert result == {"status": "aprovada"}
        doc = db.collection.return_value.add.call_args[0][0]
        assert doc["resultado"] == "sucesso"
        assert doc["operacao"] == "aprovar_atividade"
        assert doc["entidade_id"] == "act-123"
        assert doc["uid_usuario"] == "coord-uid-001"
        assert doc["role_usuario"] == "coordenacao"

    @pytest.mark.asyncio
    async def test_grava_log_erro_e_relanca(self, user_orientador):
        db = make_db_mock()
        with patch("backend.app.aspects.aspect_config.AUDIT_ENABLED", True), \
             patch("backend.app.aspects.audit.get_firestore_client", return_value=db):
            from backend.app.aspects.audit import audit_operation

            @audit_operation(operacao="op_falha", entidade="activities")
            async def handler(activity_id, current_user):
                raise ValueError("erro simulado")

            with pytest.raises(ValueError, match="erro simulado"):
                await handler(activity_id="act-err", current_user=user_orientador)

        doc = db.collection.return_value.add.call_args[0][0]
        assert doc["resultado"] == "erro"
        assert "erro simulado" in doc["detalhe_erro"]

    @pytest.mark.asyncio
    async def test_desabilitado_nao_chama_firestore(self, user_coordenacao):
        db = make_db_mock()
        with patch("backend.app.aspects.aspect_config.AUDIT_ENABLED", False), \
             patch("backend.app.aspects.audit.get_firestore_client", return_value=db):
            from backend.app.aspects.audit import audit_operation

            @audit_operation(operacao="op_off", entidade="activities")
            async def handler(current_user):
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
            async def handler(current_user):
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
        assert doc["uid_usuario"] is None
        assert doc["email_usuario"] is None

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
                tipo="atividade_aprovada",
                titulo="Atividade aprovada",
                get_mensagem_fn=lambda r, kw: f"Atividade {kw.get('activity_id')} aprovada.",
                get_destinatario_fn=lambda kw: "aluno-uid-003",
                entidade_tipo="activities",
                get_entidade_id_fn=lambda kw: kw.get("activity_id"),
            )
            async def handler(activity_id, current_user):
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
                tipo="teste_ordem",
                titulo="Ordem",
                get_mensagem_fn=lambda r, kw: "msg",
                get_destinatario_fn=lambda kw: "aluno-uid-003",
                entidade_tipo="activities",
            )
            async def handler(current_user):
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

            @trigger_alerts(
                tipo="test_off",
                titulo="Off",
                get_mensagem_fn=lambda r, kw: "msg",
                get_destinatario_fn=lambda kw: "aluno-uid-003",
                entidade_tipo="activities",
            )
            async def handler(current_user):
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

            @trigger_alerts(
                tipo="test_sem_dest",
                titulo="Sem dest",
                get_mensagem_fn=lambda r, kw: "msg",
                get_destinatario_fn=lambda kw: None,
                entidade_tipo="activities",
            )
            async def handler(current_user):
                return "ok"

            await handler(current_user=user_coordenacao)

        db.collection.assert_not_called()

    @pytest.mark.asyncio
    async def test_erro_no_alerta_nao_derruba_operacao(self, user_coordenacao):
        with patch("backend.app.aspects.aspect_config.ALERTS_ENABLED", True), \
             patch("backend.app.aspects.alerts.get_firestore_client", side_effect=Exception("firestore down")):
            from backend.app.aspects.alerts import trigger_alerts

            @trigger_alerts(
                tipo="test_resiliente",
                titulo="Resiliente",
                get_mensagem_fn=lambda r, kw: "msg",
                get_destinatario_fn=lambda kw: "aluno-uid-003",
                entidade_tipo="activities",
            )
            async def handler(current_user):
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
            @audit_operation(
                operacao="aprovar_stack",
                entidade="activities",
                get_entity_id_fn=lambda kw: kw.get("activity_id"),
            )
            @trigger_alerts(
                tipo="aprovacao_stack",
                titulo="Aprovado",
                get_mensagem_fn=lambda r, kw: f"Aprovado: {kw.get('activity_id')}",
                get_destinatario_fn=lambda kw: "aluno-uid-003",
                entidade_tipo="activities",
                get_entidade_id_fn=lambda kw: kw.get("activity_id"),
            )
            async def validate_activity(activity_id, current_user):
                return {"novo_status": "aprovada", "creditos": 10}

            result = await validate_activity(activity_id="act-stack-001", current_user=user_coordenacao)

        assert result["novo_status"] == "aprovada"
        assert len(audit_docs) == 1
        assert audit_docs[0]["resultado"] == "sucesso"
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
            @trigger_alerts(
                tipo="bloqueada",
                titulo="Nunca",
                get_mensagem_fn=lambda r, kw: "msg",
                get_destinatario_fn=lambda kw: "aluno-uid-003",
                entidade_tipo="activities",
            )
            async def validate_activity(activity_id, current_user):
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
            @trigger_alerts(
                tipo="nunca_dispara",
                titulo="Nunca",
                get_mensagem_fn=lambda r, kw: "msg",
                get_destinatario_fn=lambda kw: "aluno-uid-003",
                entidade_tipo="activities",
            )
            async def validate_activity(activity_id, current_user):
                raise ValueError("erro de negócio")

            with pytest.raises(ValueError):
                await validate_activity(activity_id="act-err", current_user=user_coordenacao)

        assert len(audit_docs) == 1
        assert audit_docs[0]["resultado"] == "erro"
        assert len(alert_docs) == 0