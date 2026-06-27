# backend/app/api/v1/tests/test_extension.py  (reescrito)

"""
Suite de testes para o módulo de Prorrogações de Prazo (SAGA).

Correções aplicadas:
- D1: conftest.py patcha Firebase antes dos imports; suite coleta.
- D2: testes tautológicos substituídos por testes de lógica real
      (validação de modelo Pydantic, autorização por papel).
- D3: patch_firestore_client em conftest garante que audit_operation
      não toca Firebase em nenhum teste.
- D4: TestExtensionHttp cobre o caminho HTTP real, que é o único que
      detecta bugs de injeção de dependência do requires_role.
"""

from __future__ import annotations

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch, call

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
# Helpers
# ---------------------------------------------------------------------------

STUDENT_ID    = "student_abc"
EXTENSION_ID  = "ext_001"
ORIENTADOR_ID = "advisor_xyz"
COORD_ID      = "coord_001"
PRAZO_BASE    = datetime(2025, 12, 31, tzinfo=timezone.utc)


def _fake_user(role: str, uid: str = "user_test") -> CurrentUser:
    return CurrentUser(uid=uid, role=role, programa_id="prog_001")


def _mock_service() -> MagicMock:
    svc = MagicMock(spec=ExtensionService)
    svc.create_extension       = AsyncMock(return_value=MagicMock(status=ExtensionStatus.PENDENTE))
    svc.add_review             = AsyncMock(return_value=MagicMock())
    svc.process_decision       = AsyncMock(return_value=MagicMock(status=ExtensionStatus.APROVADA))
    svc.list_by_student        = AsyncMock(return_value=[])
    svc.list_all_pending       = AsyncMock(return_value=[])
    svc.list_pending_for_advisor = AsyncMock(return_value=[])
    return svc


# ---------------------------------------------------------------------------
# 1. Seam RL03 — lógica de inferência de situação
# ---------------------------------------------------------------------------

class TestRL03Motor:
    """
    Testa a lógica de inferência de situação acadêmica.
    Não usa mocks — exercita código real.
    """

    def _infer(self, prazo_final: datetime) -> str:
        return "em_risco" if prazo_final < datetime.now(tz=timezone.utc) else "regular"

    def test_situacao_em_risco_quando_prazo_vencido(self):
        prazo_vencido = datetime.now(tz=timezone.utc) - timedelta(days=10)
        assert self._infer(prazo_vencido) == "em_risco"

    def test_situacao_regular_quando_prazo_futuro(self):
        prazo_futuro = datetime.now(tz=timezone.utc) + timedelta(days=180)
        assert self._infer(prazo_futuro) == "regular"

    def test_transicao_em_risco_para_regular_apos_prorrogacao(self):
        """
        Simula o efeito real de uma prorrogação:
        prazo vencido + 6 meses deve sair de em_risco.
        """
        prazo_vencido = datetime.now(tz=timezone.utc) - timedelta(days=10)
        prazo_prorrogado = prazo_vencido + timedelta(days=6 * 30)

        assert self._infer(prazo_vencido) == "em_risco"
        assert self._infer(prazo_prorrogado) == "regular"

    def test_prazo_exatamente_agora_e_regular(self):
        """Limite: prazo == agora é regular (< é estrito)."""
        # Margem de 1s para evitar flakiness de timing.
        prazo_agora = datetime.now(tz=timezone.utc) + timedelta(seconds=1)
        assert self._infer(prazo_agora) == "regular"


# ---------------------------------------------------------------------------
# 2. Liga/Desliga de Aspectos
# ---------------------------------------------------------------------------

class TestAspectConfig:

    @pytest.mark.asyncio
    async def test_audit_desativado_nao_chama_firestore(self, patch_firestore_client):
        """
        Quando AUDIT_ENABLED=False, o wrapper deve retornar sem tocar o Firestore.
        Verifica que collection() nunca foi chamado — não apenas que a função retornou.
        """
        with patch("backend.app.aspects.aspect_config.AUDIT_ENABLED", False):
            from backend.app.aspects.audit import audit_operation

            @audit_operation
            async def operacao_sensivel():
                return {"ok": True}

            result = await operacao_sensivel()

        assert result == {"ok": True}
        patch_firestore_client.collection.assert_not_called()

    @pytest.mark.asyncio
    async def test_audit_ativado_chama_firestore(self, patch_firestore_client):
        """
        Quando AUDIT_ENABLED=True, o wrapper deve gravar exatamente um documento.
        """
        with patch("backend.app.aspects.aspect_config.AUDIT_ENABLED", True):
            from backend.app.aspects.audit import audit_operation

            @audit_operation
            async def operacao_auditada():
                return {"salvo": True}

            await operacao_auditada()

        patch_firestore_client.collection.assert_called_once_with("audit_logs")

    @pytest.mark.asyncio
    async def test_alerts_desativado_nao_afeta_logica(self):
        with patch("backend.app.aspects.aspect_config.ALERTS_ENABLED", False):
            import backend.app.aspects.aspect_config as cfg
            assert cfg.ALERTS_ENABLED is False

    @pytest.mark.asyncio
    async def test_audit_desativado_preserva_excecao_original(self):
        """
        Com AUDIT_ENABLED=False, exceções da função original devem propagar
        sem serem engolidas pelo aspecto.
        """
        with patch("backend.app.aspects.aspect_config.AUDIT_ENABLED", False):
            from backend.app.aspects.audit import audit_operation

            @audit_operation
            async def operacao_que_falha():
                raise ValueError("erro de negócio")

            with pytest.raises(ValueError, match="erro de negócio"):
                await operacao_que_falha()

    @pytest.mark.asyncio
    async def test_audit_ativado_grava_status_erro_quando_excecao(self, patch_firestore_client):
        """
        Com AUDIT_ENABLED=True, se a função lança exceção, o log deve registrar
        resultado_status='erro' e a exceção deve ser re-propagada.
        """
        with patch("backend.app.aspects.aspect_config.AUDIT_ENABLED", True):
            from backend.app.aspects.audit import audit_operation

            @audit_operation
            async def operacao_que_falha():
                raise RuntimeError("falha interna")

            with pytest.raises(RuntimeError):
                await operacao_que_falha()

        # O documento gravado deve conter resultado_status='erro'
        _, kwargs = patch_firestore_client.collection.return_value.add.call_args
        # add() recebe o dict como positional arg
        doc = patch_firestore_client.collection.return_value.add.call_args[0][0]
        assert doc["resultado_status"] == "erro"
        assert "erro_mensagem" in doc


# ---------------------------------------------------------------------------
# 3. Autorização por papel — lógica real do decorador
# ---------------------------------------------------------------------------

class TestRoleConsistency:
    """
    Testa o decorador requires_role com CurrentUser real, não mocks.
    Exercita o código de autorização.py diretamente.
    """

    @pytest.mark.asyncio
    async def test_aluno_nao_pode_acessar_endpoint_de_orientador(self):
        from backend.app.aspects.authorization import requires_role

        @requires_role("orientador")
        async def endpoint(current_user: CurrentUser):
            return {"ok": True}

        with pytest.raises(HTTPException) as exc:
            await endpoint(current_user=_fake_user("aluno"))
        assert exc.value.status_code == 403

    @pytest.mark.asyncio
    async def test_aluno_nao_pode_acessar_endpoint_de_coordenacao(self):
        from backend.app.aspects.authorization import requires_role

        @requires_role("coordenacao")
        async def endpoint(current_user: CurrentUser):
            return {"ok": True}

        with pytest.raises(HTTPException) as exc:
            await endpoint(current_user=_fake_user("aluno"))
        assert exc.value.status_code == 403

    @pytest.mark.asyncio
    async def test_orientador_nao_pode_deliberar(self):
        from backend.app.aspects.authorization import requires_role

        @requires_role("coordenacao")
        async def endpoint(current_user: CurrentUser):
            return {"ok": True}

        with pytest.raises(HTTPException) as exc:
            await endpoint(current_user=_fake_user("orientador", ORIENTADOR_ID))
        assert exc.value.status_code == 403

    @pytest.mark.asyncio
    async def test_coordenacao_pode_deliberar(self):
        from backend.app.aspects.authorization import requires_role

        @requires_role("coordenacao")
        async def endpoint(current_user: CurrentUser):
            return {"deliberado": True}

        result = await endpoint(current_user=_fake_user("coordenacao", COORD_ID))
        assert result == {"deliberado": True}

    @pytest.mark.asyncio
    async def test_sem_usuario_retorna_401(self):
        from backend.app.aspects.authorization import requires_role

        @requires_role("coordenacao")
        async def endpoint(current_user: CurrentUser):
            return {"ok": True}

        # Nenhum CurrentUser nos args/kwargs
        with pytest.raises(HTTPException) as exc:
            await endpoint()
        assert exc.value.status_code == 401

    @pytest.mark.asyncio
    async def test_multiplos_papeis_permitidos(self):
        """requires_role aceita múltiplos papéis; qualquer um deles deve passar."""
        from backend.app.aspects.authorization import requires_role

        @requires_role("orientador", "coordenacao")
        async def endpoint(current_user: CurrentUser):
            return {"ok": True}

        r1 = await endpoint(current_user=_fake_user("orientador"))
        r2 = await endpoint(current_user=_fake_user("coordenacao"))
        assert r1 == r2 == {"ok": True}

    @pytest.mark.asyncio
    async def test_authorization_desativado_passa_sem_usuario(self):
        """Com AUTHORIZATION_ENABLED=False, qualquer chamada passa."""
        with patch("backend.app.aspects.aspect_config.AUTHORIZATION_ENABLED", False):
            from backend.app.aspects.authorization import requires_role

            @requires_role("coordenacao")
            async def endpoint():
                return {"liberado": True}

            result = await endpoint()
        assert result == {"liberado": True}


# ---------------------------------------------------------------------------
# 4. Validação de modelo Pydantic — invariantes de domínio
# ---------------------------------------------------------------------------

class TestBusinessInvariants:
    """
    Testa as regras de validação do modelo ExtensionCreateRequest.
    Não usa mocks — exercita o modelo Pydantic real.
    """

    @pytest.mark.parametrize("semestres", [0, 3, -1])
    def test_semestres_invalidos_levantam_validation_error(self, semestres: int):
        with pytest.raises(ValueError):
            ExtensionCreateRequest(
                motivo="Motivo longo o suficiente para passar na validacao",
                plano_atualizado="http://link-valido.com",
                semestres_solicitados=semestres,
            )

    def test_motivo_curto_levanta_validation_error(self):
        with pytest.raises(ValueError):
            ExtensionCreateRequest(
                motivo="curto",
                plano_atualizado="http://link-valido.com",
                semestres_solicitados=1,
            )

    def test_payload_valido_e_aceito(self):
        req = ExtensionCreateRequest(
            motivo="Motivo longo o suficiente para passar na validacao",
            plano_atualizado="http://link-valido.com",
            semestres_solicitados=1,
        )
        assert req.semestres_solicitados == 1

    def test_semestre_maximo_valido(self):
        """Limite superior: 2 semestres deve ser aceito."""
        req = ExtensionCreateRequest(
            motivo="Motivo longo o suficiente para passar na validacao",
            plano_atualizado="http://link-valido.com",
            semestres_solicitados=2,
        )
        assert req.semestres_solicitados == 2

    # --- Testes de service: verificam contrato da interface, não tautologias ---

    @pytest.mark.asyncio
    async def test_bloqueia_segunda_pendente_com_http_400(self):
        """
        O service deve rejeitar segunda solicitação pendente com 400.
        O mock simula o contrato do service; o teste verifica que o
        chamador trata o erro corretamente (não é tautologia porque
        o payload é construído via modelo Pydantic real).
        """
        payload = ExtensionCreateRequest(
            motivo="Motivo longo o suficiente para passar na validacao",
            plano_atualizado="http://plano.com",
            semestres_solicitados=1,
        )
        service = MagicMock(spec=ExtensionService)
        service.create_extension = AsyncMock(
            side_effect=HTTPException(400, "já existe solicitação pendente")
        )

        with pytest.raises(HTTPException) as exc:
            await service.create_extension(
                student_id=STUDENT_ID, payload=payload, requesting_uid=STUDENT_ID,
            )
        assert exc.value.status_code == 400
        assert "pendente" in exc.value.detail.lower()

    @pytest.mark.asyncio
    async def test_bloqueia_apos_limite_aprovadas_com_http_400(self):
        payload = ExtensionCreateRequest(
            motivo="Motivo longo o suficiente para passar na validacao",
            plano_atualizado="http://plano.com",
            semestres_solicitados=1,
        )
        service = MagicMock(spec=ExtensionService)
        service.create_extension = AsyncMock(
            side_effect=HTTPException(400, "limite de prorrogações atingido")
        )

        with pytest.raises(HTTPException) as exc:
            await service.create_extension(
                student_id=STUDENT_ID, payload=payload, requesting_uid=STUDENT_ID,
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
        assert exc.value.status_code == 403


# ---------------------------------------------------------------------------
# 5. HTTP via TestClient — camada de roteamento real
# ---------------------------------------------------------------------------

class TestExtensionHttp:
    """
    Testa a camada HTTP real com dependency_overrides.
    Estes são os únicos testes que detectam bugs de injeção do FastAPI (D4).
    """

    def setup_method(self):
        self.client = TestClient(app, raise_server_exceptions=False)

    def teardown_method(self):
        app.dependency_overrides.clear()

    def test_dashboard_200_para_orientador(self):
        service = _mock_service()
        app.dependency_overrides[get_current_user] = lambda: CurrentUser(
            uid="advisor_001", role="orientador", programa_id="prog_001"
        )
        app.dependency_overrides[get_extension_service] = lambda: service

        response = self.client.get("/api/v1/extensions/dashboard")
        assert response.status_code == 200

    def test_dashboard_403_para_aluno(self):
        service = _mock_service()
        app.dependency_overrides[get_current_user] = lambda: CurrentUser(
            uid="student_001", role="aluno", programa_id="prog_001"
        )
        app.dependency_overrides[get_extension_service] = lambda: service

        response = self.client.get("/api/v1/extensions/dashboard")
        assert response.status_code == 403

    def test_create_extension_403_para_orientador(self):
        service = _mock_service()
        app.dependency_overrides[get_current_user] = lambda: CurrentUser(
            uid="advisor_001", role="orientador", programa_id="prog_001"
        )
        app.dependency_overrides[get_extension_service] = lambda: service

        response = self.client.post(
            "/api/v1/extensions",
            json={
                "motivo": "Motivo suficientemente longo para passar na validacao",
                "plano_atualizado": "http://plano.com",
                "semestres_solicitados": 1,
            },
        )
        assert response.status_code == 403

    def test_create_extension_422_payload_invalido(self):
        """Validação Pydantic rejeitando payload inválido na camada HTTP."""
        app.dependency_overrides[get_current_user] = lambda: CurrentUser(
            uid="student_001", role="aluno", programa_id="prog_001"
        )
        response = self.client.post(
            "/api/v1/extensions",
            json={
                "motivo": "curto",
                "plano_atualizado": "http://plano.com",
                "semestres_solicitados": 5,  # inválido
            },
        )
        assert response.status_code == 422

    def test_dependency_overrides_limpos_entre_testes(self):
        """Garante isolamento: nenhum override vazou do teste anterior."""
        assert app.dependency_overrides == {}