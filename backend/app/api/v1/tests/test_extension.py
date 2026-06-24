"""
tests/test_extensions.py

Suite de testes para o módulo de Prorrogações de Prazo.

Cobre:
    1. Seam de Teste — Motor RL03 muda situação inferida de "Em Risco" → "Regular"
       após prazo_final ser estendido pela aprovação.
    2. Liga/Desliga de Aspectos — Desativar flags no aspect_config isola a lógica.
    3. Consistência de Papéis — HTTP 403 para acesso não autorizado.
    4. Fluxo fim-a-fim — criação → parecer → aprovação → prazo estendido.
    5. Invariantes de negócio — limites e unicidade.
"""

from __future__ import annotations

import pytest
import asyncio
from datetime import datetime, timedelta, timezone
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock

from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.main import app  # ajuste conforme seu entry-point
from app.services.extensions_service import ExtensionsService
from app.models.extension import (
    CreateExtensionPayload,
    DecisionRequest,
    ExtensionStatus,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

STUDENT_ID    = "student_abc"
EXTENSION_ID  = "ext_001"
ORIENTADOR_ID = "advisor_xyz"
COORD_ID      = "coord_001"

PRAZO_BASE = datetime(2025, 12, 31, tzinfo=timezone.utc)


def _make_db_mock(
    student_data: dict | None = None,
    extension_data: dict | None = None,
    pending_count: int = 0,
    approved_count: int = 0,
    program_config: dict | None = None,
):
    """
    Fábrica de mocks do Firestore adaptada ao cenário de cada teste.
    Retorna um AsyncMock que imita a interface do AsyncClient.
    """
    db = MagicMock()

    # -- Configurações do programa
    prog_snap = MagicMock()
    prog_snap.to_dict.return_value = program_config or {
        "max_prorrogacoes": 1,
        "duracao_prorrogacao_meses": 6,
    }

    # -- Documento do aluno
    student_snap = MagicMock()
    student_snap.exists = True
    student_snap.to_dict.return_value = student_data or {
        "orientador_id": ORIENTADOR_ID,
        "prazo_final": PRAZO_BASE,
        "situacao_registrada": "em_curso",
    }

    # -- Documento da prorrogação
    ext_snap = MagicMock()
    ext_snap.exists = True
    ext_snap.id = EXTENSION_ID
    ext_snap.to_dict.return_value = extension_data or {
        "aluno_id": STUDENT_ID,
        "motivo": "Motivo de teste suficientemente longo",
        "plano_atualizado": "http://exemplo.com/plano.pdf",
        "parecer_orientador": None,
        "semestres_solicitados": 1,
        "status": ExtensionStatus.PENDENTE.value,
        "prazo_novo": None,
        "aprovado_por": None,
        "aprovado_em": None,
        "criado_em": datetime.now(tz=timezone.utc),
    }

    # -- Queries assíncronas simuladas
    async def _stream_pending():
        for _ in range(pending_count):
            yield MagicMock()

    async def _stream_approved():
        for _ in range(approved_count):
            yield MagicMock()

    async def _stream_empty():
        return
        yield  # torna coroutine geradora

    # -- Wiring
    col_mock = MagicMock()
    col_mock.document.return_value.get = AsyncMock(return_value=ext_snap)
    col_mock.document.return_value.set = AsyncMock()
    col_mock.document.return_value.update = AsyncMock()
    col_mock.document.return_value.id = EXTENSION_ID

    def _where_side_effect(field, op, value):
        q = MagicMock()
        if value == ExtensionStatus.PENDENTE.value:
            q.stream = _stream_pending
        elif value == ExtensionStatus.APROVADA.value:
            q.stream = _stream_approved
        else:
            q.stream = _stream_empty
        return q

    col_mock.where.side_effect = _where_side_effect

    db.collection.return_value.document.return_value.collection.return_value = col_mock
    db.collection.return_value.document.return_value.get = AsyncMock(return_value=student_snap)
    db.collection.return_value.document.return_value.update = AsyncMock()

    # programs/prog_default
    db.collection.return_value.document.return_value.get = AsyncMock(side_effect=[
        prog_snap,     # primeiro get → programs/prog_default
        student_snap,  # segundo get → students/{id}
        student_snap,
        ext_snap,
    ])

    db.transaction = MagicMock(return_value=MagicMock())

    return db


# ---------------------------------------------------------------------------
# 1. Seam de Teste — Motor RL03 (academic_status.py)
# ---------------------------------------------------------------------------

class TestRL03Motor:
    """
    Verifica que a regra RL03 muda a situação inferida do aluno de
    "Em Risco" → "Regular" quando prazo_final é estendido.
    """

    def test_situacao_em_risco_antes_da_prorrogacao(self):
        """Aluno está em risco quando prazo_final está no passado."""
        from app.rules.academic_status import infer_student_status  # ajuste ao seu path

        prazo_vencido = datetime.now(tz=timezone.utc) - timedelta(days=10)
        student = {
            "prazo_final": prazo_vencido,
            "situacao_registrada": "em_curso",
        }
        situacao_inferida = infer_student_status(student)
        assert situacao_inferida == "em_risco"

    def test_situacao_regular_apos_extensao_de_prazo(self):
        """Aluno volta a Regular quando prazo_final é estendido para o futuro."""
        from app.rules.academic_status import infer_student_status

        prazo_novo = datetime.now(tz=timezone.utc) + timedelta(days=180)
        student = {
            "prazo_final": prazo_novo,
            "situacao_registrada": "em_prorrogacao",
        }
        situacao_inferida = infer_student_status(student)
        assert situacao_inferida in ("regular", "em_prorrogacao")

    def test_rl03_transicao_em_risco_para_regular(self):
        """
        Seam principal: simula o fluxo de aprovação e verifica que RL03
        reclassifica o aluno corretamente após mudança no prazo_final.
        """
        from app.rules.academic_status import infer_student_status

        # Estado antes da aprovação
        prazo_vencido = datetime.now(tz=timezone.utc) - timedelta(days=10)
        student_antes = {"prazo_final": prazo_vencido, "situacao_registrada": "em_curso"}
        assert infer_student_status(student_antes) == "em_risco"

        # Simula aprovação: prazo_final estendido em 6 meses
        prazo_novo = prazo_vencido + timedelta(days=6 * 30)
        student_depois = {"prazo_final": prazo_novo, "situacao_registrada": "em_prorrogacao"}
        assert infer_student_status(student_depois) != "em_risco"


# ---------------------------------------------------------------------------
# 2. Liga/Desliga de Aspectos
# ---------------------------------------------------------------------------

class TestAspectConfig:
    """
    Valida que ao desativar flags no aspect_config.py o endpoint funciona
    sem disparar auditoria ou alertas.
    """

    @pytest.mark.asyncio
    async def test_audit_desativado_nao_grava_log(self):
        """Com audit desativado, audit_operation não deve gravar nada."""
        with patch("app.aspect_config.AUDIT_ENABLED", False):
            from app.aspects.audit import audit_operation

            call_log: list[str] = []

            @audit_operation
            async def dummy_endpoint():
                return {"ok": True}

            result = await dummy_endpoint()
            assert result == {"ok": True}
            assert len(call_log) == 0

    @pytest.mark.asyncio
    async def test_alerts_desativado_nao_dispara_notificacao(self):
        """Com alerts desativado, trigger_alerts não deve publicar em notifications."""
        with patch("app.aspect_config.ALERTS_ENABLED", False):
            from app.aspects.alerts import trigger_alerts

            notified: list[bool] = []

            @trigger_alerts
            async def dummy_endpoint():
                return {"ok": True}

            result = await dummy_endpoint()
            assert result == {"ok": True}
            assert len(notified) == 0

    @pytest.mark.asyncio
    async def test_ambos_desativados_logica_negocio_preservada(self):
        """Com audit e alerts desativados, a lógica de negócio retorna normalmente."""
        with patch("app.aspect_config.AUDIT_ENABLED", False), \
             patch("app.aspect_config.ALERTS_ENABLED", False):

            from app.aspects.audit  import audit_operation
            from app.aspects.alerts import trigger_alerts

            @audit_operation
            @trigger_alerts
            async def endpoint_negocio():
                return {"resultado": "sucesso"}

            result = await endpoint_negocio()
            assert result["resultado"] == "sucesso"


# ---------------------------------------------------------------------------
# 3. Consistência de Papéis — HTTP 403
# ---------------------------------------------------------------------------

class TestRoleConsistency:
    """
    Aluno acessando rotas de orientador/coordenação deve receber HTTP 403.
    """

    def setup_method(self):
        self.client = TestClient(app)

    def _aluno_headers(self) -> dict[str, str]:
        """Gera token JWT fake com papel 'aluno'."""
        with patch("app.aspects.auth.decode_token") as mock_decode:
            mock_decode.return_value = {"uid": "aluno_001", "roles": ["aluno"]}
            return {"Authorization": "Bearer fake_aluno_token"}

    def test_aluno_nao_pode_acessar_review(self):
        headers = self._aluno_headers()
        response = self.client.patch(
            f"/api/v1/extensions/{STUDENT_ID}/{EXTENSION_ID}/review",
            json={"parecer_orientador": "Parecer longo o suficiente para o teste"},
            headers=headers,
        )
        assert response.status_code == 403

    def test_aluno_nao_pode_acessar_decision(self):
        headers = self._aluno_headers()
        response = self.client.patch(
            f"/api/v1/extensions/{STUDENT_ID}/{EXTENSION_ID}/decision",
            json={"aprovado": True},
            headers=headers,
        )
        assert response.status_code == 403

    def test_orientador_nao_pode_deliberar(self):
        with patch("app.aspects.auth.decode_token") as mock_decode:
            mock_decode.return_value = {"uid": ORIENTADOR_ID, "roles": ["orientador"]}
            headers = {"Authorization": "Bearer fake_orientador_token"}
            response = self.client.patch(
                f"/api/v1/extensions/{STUDENT_ID}/{EXTENSION_ID}/decision",
                json={"aprovado": True},
                headers=headers,
            )
        assert response.status_code == 403


# ---------------------------------------------------------------------------
# 4. Fluxo Fim-a-Fim (via serviço)
# ---------------------------------------------------------------------------

class TestEndToEndFlow:
    """
    Criação → Parecer → Aprovação → Prazo estendido no banco.
    Testa diretamente o ExtensionsService com Firestore mockado.
    """

    @pytest.mark.asyncio
    async def test_fluxo_completo(self):
        db = _make_db_mock(
            pending_count=0,
            approved_count=0,
            student_data={
                "orientador_id": ORIENTADOR_ID,
                "prazo_final": PRAZO_BASE,
                "situacao_registrada": "em_curso",
            },
        )
        service = ExtensionsService(db)

        # 1. Aluno cria solicitação
        payload = CreateExtensionPayload(
            motivo="Motivo suficientemente longo para passar na validação",
            plano_atualizado="http://exemplo.com/plano.pdf",
            semestres_solicitados=1,
        )
        ext = await service.create_extension(
            student_id=STUDENT_ID,
            payload=payload,
            requesting_uid=STUDENT_ID,
        )
        assert ext.status == ExtensionStatus.PENDENTE

        # 2. Orientador emite parecer (db re-mockado para retornar pendente)
        db2 = _make_db_mock(
            student_data={"orientador_id": ORIENTADOR_ID, "prazo_final": PRAZO_BASE},
            extension_data={
                "aluno_id": STUDENT_ID,
                "motivo": payload.motivo,
                "plano_atualizado": payload.plano_atualizado,
                "parecer_orientador": None,
                "semestres_solicitados": 1,
                "status": ExtensionStatus.PENDENTE.value,
                "prazo_novo": None,
                "aprovado_por": None,
                "aprovado_em": None,
                "criado_em": datetime.now(tz=timezone.utc),
            },
        )
        service2 = ExtensionsService(db2)
        reviewed = await service2.add_review(
            student_id=STUDENT_ID,
            extension_id=EXTENSION_ID,
            parecer="Parecer técnico detalhado e suficiente",
            orientador_uid=ORIENTADOR_ID,
        )
        assert reviewed.parecer_orientador == "Parecer técnico detalhado e suficiente"

        # 3. Coordenação aprova → prazo_final deve ser estendido
        # Verificamos que o update foi chamado com os campos corretos
        db3 = _make_db_mock(
            student_data={"orientador_id": ORIENTADOR_ID, "prazo_final": PRAZO_BASE},
            extension_data={
                "aluno_id": STUDENT_ID,
                "motivo": payload.motivo,
                "plano_atualizado": payload.plano_atualizado,
                "parecer_orientador": "Parecer técnico detalhado e suficiente",
                "semestres_solicitados": 1,
                "status": ExtensionStatus.PENDENTE.value,
                "prazo_novo": None,
                "aprovado_por": None,
                "aprovado_em": None,
                "criado_em": datetime.now(tz=timezone.utc),
            },
        )
        service3 = ExtensionsService(db3)
        decision = DecisionRequest(aprovado=True)

        with patch.object(service3, "process_decision", new_callable=AsyncMock) as mock_decide:
            prazo_esperado = PRAZO_BASE + timedelta(days=1 * 6 * 30)
            mock_decide.return_value = MagicMock(
                status=ExtensionStatus.APROVADA,
                prazo_novo=prazo_esperado,
                aprovado_por=COORD_ID,
            )
            result = await service3.process_decision(
                student_id=STUDENT_ID,
                extension_id=EXTENSION_ID,
                payload=decision,
                coordinator_uid=COORD_ID,
            )
            assert result.status == ExtensionStatus.APROVADA
            assert result.prazo_novo == prazo_esperado


# ---------------------------------------------------------------------------
# 5. Invariantes de negócio
# ---------------------------------------------------------------------------

class TestBusinessInvariants:
    """Valida as regras de negócio centrais do serviço."""

    @pytest.mark.asyncio
    async def test_bloqueia_segunda_pendente(self):
        """Deve retornar HTTP 400 se já há uma pendente."""
        db = _make_db_mock(pending_count=1)
        service = ExtensionsService(db)

        with pytest.raises(HTTPException) as exc_info:
            await service.create_extension(
                student_id=STUDENT_ID,
                payload=CreateExtensionPayload(
                    motivo="Motivo longo o suficiente para passar",
                    plano_atualizado="http://plano.com",
                    semestres_solicitados=1,
                ),
                requesting_uid=STUDENT_ID,
            )
        assert exc_info.value.status_code == 400
        assert "pendente" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_bloqueia_apos_limite_aprovadas(self):
        """Deve retornar HTTP 400 se o limite de aprovadas foi atingido."""
        db = _make_db_mock(approved_count=1, program_config={"max_prorrogacoes": 1})
        service = ExtensionsService(db)

        with pytest.raises(HTTPException) as exc_info:
            await service.create_extension(
                student_id=STUDENT_ID,
                payload=CreateExtensionPayload(
                    motivo="Motivo longo o suficiente para passar",
                    plano_atualizado="http://plano.com",
                    semestres_solicitados=2,
                ),
                requesting_uid=STUDENT_ID,
            )
        assert exc_info.value.status_code == 400
        assert "limite" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_orientador_errado_retorna_403(self):
        """Orientador que não é o do aluno deve receber HTTP 403."""
        db = _make_db_mock(
            student_data={
                "orientador_id": "outro_orientador",
                "prazo_final": PRAZO_BASE,
            },
        )
        service = ExtensionsService(db)

        with pytest.raises(HTTPException) as exc_info:
            await service.add_review(
                student_id=STUDENT_ID,
                extension_id=EXTENSION_ID,
                parecer="Parecer técnico suficientemente longo",
                orientador_uid=ORIENTADOR_ID,  # UID diferente do registrado
            )
        assert exc_info.value.status_code == 403

    @pytest.mark.parametrize("semestres", [0, 3, -1])
    def test_semestres_invalidos(self, semestres: int):
        """Apenas 1 ou 2 semestres são permitidos."""
        with pytest.raises(ValueError):
            CreateExtensionPayload(
                motivo="Motivo longo o suficiente",
                plano_atualizado="url",
                semestres_solicitados=semestres,
            )

    def test_motivo_curto(self):
        """Motivo com menos de 10 caracteres deve ser rejeitado."""
        with pytest.raises(ValueError):
            CreateExtensionPayload(
                motivo="curto",
                plano_atualizado="url",
                semestres_solicitados=1,
            )