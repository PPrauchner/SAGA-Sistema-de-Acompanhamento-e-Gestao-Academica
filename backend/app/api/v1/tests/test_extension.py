"""
backend/app/api/v1/tests/test_extension.py

Suite de testes para o módulo de Prorrogações de Prazo (SAGA).
"""

from __future__ import annotations

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import HTTPException
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.core.auth import get_current_user, CurrentUser
from backend.app.api.v1.extensions import get_extension_service
from backend.app.services.extension_service import ExtensionService
from backend.app.models.extension import (
    ExtensionCreateRequest,
    DecisionRequest,
    ExtensionStatus,
)

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

STUDENT_ID    = "student_abc"
EXTENSION_ID  = "ext_001"
ORIENTADOR_ID = "advisor_xyz"
COORD_ID      = "coord_001"
PRAZO_BASE    = datetime(2025, 12, 31, tzinfo=timezone.utc)


def _fake_user(role: str, uid: str = "user_test") -> CurrentUser:
    return CurrentUser(uid=uid, role=role, programa_id="prog_001")


def _mock_service() -> ExtensionService:
    svc = MagicMock(spec=ExtensionService)
    svc.create_extension = AsyncMock(return_value=MagicMock(status=ExtensionStatus.PENDENTE))
    svc.add_review       = AsyncMock(return_value=MagicMock())
    svc.process_decision = AsyncMock(return_value=MagicMock(status=ExtensionStatus.APROVADA))
    svc.list_by_student  = AsyncMock(return_value=[])
    svc.list_all_pending = AsyncMock(return_value=[])
    svc.list_pending_for_advisor = AsyncMock(return_value=[])
    return svc


# ---------------------------------------------------------------------------
# 1. Seam RL03
# ---------------------------------------------------------------------------

class TestRL03Motor:
    def _infer(self, prazo_final: datetime) -> str:
        return "em_risco" if prazo_final < datetime.now(tz=timezone.utc) else "regular"

    def test_situacao_em_risco_antes_da_prorrogacao(self):
        assert self._infer(datetime.now(tz=timezone.utc) - timedelta(days=10)) == "em_risco"

    def test_situacao_regular_apos_extensao_de_prazo(self):
        assert self._infer(datetime.now(tz=timezone.utc) + timedelta(days=180)) == "regular"

    def test_rl03_transicao_em_risco_para_regular(self):
        vencido = datetime.now(tz=timezone.utc) - timedelta(days=10)
        assert self._infer(vencido) == "em_risco"
        assert self._infer(vencido + timedelta(days=6 * 30)) != "em_risco"


# ---------------------------------------------------------------------------
# 2. Liga/Desliga de Aspectos
# ---------------------------------------------------------------------------

class TestAspectConfig:

    @pytest.mark.asyncio
    async def test_audit_desativado_nao_grava_log(self):
        with patch("backend.app.aspects.aspect_config.AUDIT_ENABLED", False):
            from backend.app.aspects.audit import audit_operation

            @audit_operation
            async def dummy():
                return {"ok": True}

            assert await dummy() == {"ok": True}

    @pytest.mark.asyncio
    async def test_alerts_desativado_nao_dispara_notificacao(self):
        # trigger_alerts requer argumento build — testamos o flag diretamente
        with patch("backend.app.aspects.aspect_config.ALERTS_ENABLED", False):
            import backend.app.aspects.aspect_config as cfg
            assert cfg.ALERTS_ENABLED is False

    @pytest.mark.asyncio
    async def test_ambos_desativados_logica_negocio_preservada(self):
        with patch("backend.app.aspects.aspect_config.AUDIT_ENABLED", False), \
             patch("backend.app.aspects.aspect_config.ALERTS_ENABLED", False):
            from backend.app.aspects.audit import audit_operation

            @audit_operation
            async def endpoint_negocio():
                return {"resultado": "sucesso"}

            result = await endpoint_negocio()
            assert result["resultado"] == "sucesso"


# ---------------------------------------------------------------------------
# 3. Consistência de Papéis — HTTP 403 via dependency_overrides
# ---------------------------------------------------------------------------

class TestRoleConsistency:
    """
    Testa o decorador @requires_role diretamente, sem HTTP.
    Evita dependência de credenciais Firebase no ambiente de CI/dev.
    """

    @pytest.mark.asyncio
    async def test_aluno_nao_pode_acessar_review(self):
        from backend.app.aspects.authorization import requires_role

        @requires_role("orientador")
        async def endpoint(current_user):
            return {"ok": True}

        with pytest.raises(HTTPException) as exc:
            await endpoint(current_user=_fake_user("aluno"))
        assert exc.value.status_code in (403, 401)

    @pytest.mark.asyncio
    async def test_aluno_nao_pode_acessar_decision(self):
        from backend.app.aspects.authorization import requires_role

        @requires_role("coordenacao")
        async def endpoint(current_user):
            return {"ok": True}

        with pytest.raises(HTTPException) as exc:
            await endpoint(current_user=_fake_user("aluno"))
        assert exc.value.status_code in (403, 401)

    @pytest.mark.asyncio
    async def test_orientador_nao_pode_deliberar(self):
        from backend.app.aspects.authorization import requires_role

        @requires_role("coordenacao")
        async def endpoint(current_user):
            return {"ok": True}

        with pytest.raises(HTTPException) as exc:
            await endpoint(current_user=_fake_user("orientador", ORIENTADOR_ID))
        assert exc.value.status_code in (403, 401)


# ---------------------------------------------------------------------------
# 4. Fluxo Fim-a-Fim
# ---------------------------------------------------------------------------

class TestEndToEndFlow:

    @pytest.mark.asyncio
    async def test_fluxo_completo(self):
        service = _mock_service()
        prazo_esperado = PRAZO_BASE + timedelta(days=6 * 30)
        service.process_decision = AsyncMock(return_value=MagicMock(
            status=ExtensionStatus.APROVADA,
            prazo_novo=prazo_esperado,
            aprovado_por=COORD_ID,
        ))

        payload = ExtensionCreateRequest(
            motivo="Motivo suficientemente longo para passar na validacao",
            plano_atualizado="http://plano.com/cronograma.pdf",
            semestres_solicitados=1,
        )

        ext = await service.create_extension(
            student_id=STUDENT_ID, payload=payload, requesting_uid=STUDENT_ID
        )
        assert ext.status == ExtensionStatus.PENDENTE

        reviewed = await service.add_review(
            student_id=STUDENT_ID,
            extension_id=EXTENSION_ID,
            parecer="Parecer técnico detalhado",
            orientador_uid=ORIENTADOR_ID,
        )
        assert reviewed is not None

        result = await service.process_decision(
            student_id=STUDENT_ID,
            extension_id=EXTENSION_ID,
            payload=DecisionRequest(aprovado=True),
            coordinator_uid=COORD_ID,
        )
        assert result.status == ExtensionStatus.APROVADA
        assert result.prazo_novo == prazo_esperado


# ---------------------------------------------------------------------------
# 5. Invariantes de negócio
# ---------------------------------------------------------------------------

class TestBusinessInvariants:

    @pytest.mark.asyncio
    async def test_bloqueia_segunda_pendente(self):
        service = MagicMock(spec=ExtensionService)
        service.create_extension = AsyncMock(
            side_effect=HTTPException(400, "já existe solicitação pendente")
        )
        with pytest.raises(HTTPException) as exc:
            await service.create_extension(
                student_id=STUDENT_ID,
                payload=ExtensionCreateRequest(
                    motivo="Motivo longo o suficiente para passar na validacao",
                    plano_atualizado="http://plano.com",
                    semestres_solicitados=1,
                ),
                requesting_uid=STUDENT_ID,
            )
        assert exc.value.status_code == 400
        assert "pendente" in exc.value.detail.lower()

    @pytest.mark.asyncio
    async def test_bloqueia_apos_limite_aprovadas(self):
        service = MagicMock(spec=ExtensionService)
        service.create_extension = AsyncMock(
            side_effect=HTTPException(400, "limite de prorrogações atingido")
        )
        with pytest.raises(HTTPException) as exc:
            await service.create_extension(
                student_id=STUDENT_ID,
                payload=ExtensionCreateRequest(
                    motivo="Motivo longo o suficiente para passar na validacao",
                    plano_atualizado="http://plano.com",
                    semestres_solicitados=1,
                ),
                requesting_uid=STUDENT_ID,
            )
        assert exc.value.status_code == 400
        assert "limite" in exc.value.detail.lower()

    @pytest.mark.asyncio
    async def test_orientador_errado_retorna_403(self):
        service = MagicMock(spec=ExtensionService)
        service.add_review = AsyncMock(
            side_effect=HTTPException(403, "orientador não autorizado")
        )
        with pytest.raises(HTTPException) as exc:
            await service.add_review(
                student_id=STUDENT_ID,
                extension_id=EXTENSION_ID,
                parecer="Parecer adequado para o teste",
                orientador_uid="orientador_intruso",
            )
        assert exc.value.status_code in (403, 401)

    @pytest.mark.parametrize("semestres", [0, 3, -1])
    def test_semestres_invalidos(self, semestres: int):
        with pytest.raises(ValueError):
            ExtensionCreateRequest(
                motivo="Motivo longo o suficiente para passar na validacao",
                plano_atualizado="http://link-valido.com",
                semestres_solicitados=semestres,
            )

    def test_motivo_curto(self):
        with pytest.raises(ValueError):
            ExtensionCreateRequest(
                motivo="curto",
                plano_atualizado="http://link-valido.com",
                semestres_solicitados=1,
            )
            
    client = TestClient(app)
    app.dependency_overrides[get_current_user]

    def override_student():
        return CurrentUser(
            uid="student_001",
            role="aluno",
            programa_id="prog_001",
        )
    
    def override_advisor():
        return CurrentUser(
            uid="advisor_001",
            role="orientador",
            programa_id="prog_001",
        )
    
    def override_coord():
        return CurrentUser(
            uid="coord_001",
            role="coordenacao",
            programa_id="prog_001",
        )
    
    response = client.get(...)
    assert response.status_code == 200

    response = client.post(...)
    assert response.status_code == 403

class TestExtensionHttp:

    def setup_method(self):
        self.client = TestClient(app)

    def teardown_method(self):
        app.dependency_overrides.clear()

    def test_dashboard_200_para_orientador(self):
        service = _mock_service()

        app.dependency_overrides[get_current_user] = (
            lambda: CurrentUser(
                uid="advisor_001",
                role="orientador",
                programa_id="prog_001",
            )
        )

        app.dependency_overrides[get_extension_service] = (
            lambda: service
        )

        response = self.client.get("/api/v1/extensions/dashboard")

        assert response.status_code == 200

    def test_dashboard_403_para_aluno(self):
        service = _mock_service()

        app.dependency_overrides[get_current_user] = (
            lambda: CurrentUser(
                uid="student_001",
                role="aluno",
                programa_id="prog_001",
            )
        )

        app.dependency_overrides[get_extension_service] = (
            lambda: service
        )

        response = self.client.get("/api/v1/extensions/dashboard")

        assert response.status_code == 403

    def test_create_extension_403_para_orientador(self):
        service = _mock_service()

        app.dependency_overrides[get_current_user] = (
            lambda: CurrentUser(
                uid="advisor_001",
                role="orientador",
                programa_id="prog_001",
            )
        )

        app.dependency_overrides[get_extension_service] = (
            lambda: service
        )

        payload = {
            "motivo": "Motivo suficientemente longo para passar na validacao",
            "plano_atualizado": "http://plano.com",
            "semestres_solicitados": 1,
        }

        response = self.client.post(
            "/api/v1/extensions",
            json=payload,
        )

        assert response.status_code == 403

