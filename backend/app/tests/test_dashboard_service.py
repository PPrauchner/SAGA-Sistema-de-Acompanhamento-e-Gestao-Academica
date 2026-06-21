"""
Testes TDD do DashboardService — ciclo red-green por comportamento.

Mocks na fronteira de I/O (repositórios Firestore). Cada teste verifica um
comportamento observável do serviço público, não detalhes de implementação.
"""

from __future__ import annotations

import os

# Garantir variáveis de ambiente antes de qualquer import do app
os.environ.setdefault("FIREBASE_PROJECT_ID", "test-project")
os.environ.setdefault("FIREBASE_PRIVATE_KEY", "test-key")
os.environ.setdefault("FIREBASE_CLIENT_EMAIL", "test@test.iam.gserviceaccount.com")

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest

from backend.app.models.dashboard import AlunoDashboardResponse
from fastapi import HTTPException


# ─── Fixtures ────────────────────────────────────────────────────────────────

def _make_student(overrides: dict | None = None) -> dict:
    """Cria documento student para testes com valores padrão razoáveis."""
    base = {
        "id": "stu_001",
        "uid": "uid_aluno_001",
        "nome": "Maria Silva",
        "email": "maria@test.com",
        "matricula": "2024001",
        "orientador_id": "adv_001",
        "programa_id": "prog_default",
        "nivel": "mestrado",
        "situacao_registrada": "regular",
        "situacao_inferida": "regular",
        "data_ingresso": datetime(2024, 3, 1, tzinfo=timezone.utc),
        "prazo_final": datetime(2026, 3, 1, tzinfo=timezone.utc),
        "qualificacao_aprovada": False,
        "proficiencia_comprovada": False,
    }
    if overrides:
        base.update(overrides)
    return base


# ─── Tracer Bullet: aluno vê próprio dashboard ──────────────────────────────

@pytest.mark.asyncio
async def test_aluno_dashboard_returns_basic_student_data():
    """Tracer bullet: get_aluno_dashboard retorna dados básicos do aluno."""
    from backend.app.services.dashboard_service import DashboardService

    student = _make_student()

    with (
        patch(
            "backend.app.services.dashboard_service.StudentRepository"
        ) as MockStudentRepo,
        patch(
            "backend.app.services.dashboard_service.ActivityRepository"
        ) as MockActivityRepo,
        patch(
            "backend.app.services.dashboard_service.ActivityTypeRepository"
        ) as MockActivityTypeRepo,
    ):
        MockStudentRepo.return_value.get = AsyncMock(return_value=student)
        MockStudentRepo.return_value.list_all = AsyncMock(return_value=[student])
        MockActivityRepo.return_value.list_by_student = AsyncMock(return_value=[])
        MockActivityTypeRepo.return_value.list_all = AsyncMock(return_value=[])

        service = DashboardService()
        result = await service.get_aluno_dashboard("stu_001")

    assert isinstance(result, AlunoDashboardResponse)
    assert result.student_id == "stu_001"
    assert result.nome == "Maria Silva"
    assert result.situacao_registrada == "regular"
    assert result.situacao_inferida == "regular"
    assert result.conflito_situacao is False

    MockStudentRepo.return_value.get.assert_called_once_with("stu_001")
    MockActivityRepo.return_value.list_by_student.assert_called_once_with("stu_001")
    MockActivityTypeRepo.return_value.list_all.assert_called_once()


# ─── Cycle 2: conflito de situação ──────────────────────────────────────────

@pytest.mark.asyncio
async def test_aluno_dashboard_detects_conflito_situacao():
    """Quando situacao_registrada != situacao_inferida, conflito_situacao = True."""
    from backend.app.services.dashboard_service import DashboardService

    student = _make_student({
        "situacao_registrada": "regular",
        "situacao_inferida": "em_risco",
    })

    with (
        patch("backend.app.services.dashboard_service.StudentRepository") as MockSR,
        patch("backend.app.services.dashboard_service.ActivityRepository") as MockAR,
        patch("backend.app.services.dashboard_service.ActivityTypeRepository") as MockATR,
    ):
        MockSR.return_value.get = AsyncMock(return_value=student)
        MockAR.return_value.list_by_student = AsyncMock(return_value=[])
        MockATR.return_value.list_all = AsyncMock(return_value=[])

        service = DashboardService()
        result = await service.get_aluno_dashboard("stu_001")

    assert result.conflito_situacao is True
    assert result.situacao_registrada == "regular"
    assert result.situacao_inferida == "em_risco"

    MockSR.return_value.get.assert_called_once_with("stu_001")


# ─── Cycle 3: créditos por grupo ────────────────────────────────────────────

@pytest.mark.asyncio
async def test_aluno_dashboard_aggregates_credits_by_group():
    """Créditos são agregados por categoria do activity_type."""
    from backend.app.services.dashboard_service import DashboardService

    student = _make_student()
    activities = [
        {"id": "a1", "status": "aprovado", "creditos_concedidos": 4.0,
         "tipo_id": "t_basico", "producao_id": None},
        {"id": "a2", "status": "aprovado", "creditos_concedidos": 3.0,
         "tipo_id": "t_especifico", "producao_id": None},
        {"id": "a3", "status": "aprovado", "creditos_concedidos": 2.0,
         "tipo_id": "t_tecnologico", "producao_id": None},
        {"id": "a4", "status": "enviado", "creditos_concedidos": 4.0,
         "tipo_id": "t_basico", "producao_id": None},  # não-aprovado, ignorar
    ]

    with (
        patch("backend.app.services.dashboard_service.StudentRepository") as MockSR,
        patch("backend.app.services.dashboard_service.ActivityRepository") as MockAR,
        patch("backend.app.services.dashboard_service.ActivityTypeRepository") as MockATR,
    ):
        MockSR.return_value.get = AsyncMock(return_value=student)
        MockAR.return_value.list_by_student = AsyncMock(return_value=activities)
        MockATR.return_value.list_all = AsyncMock(return_value=[
            {"id": "t_basico", "categoria": "basico"},
            {"id": "t_especifico", "categoria": "especifico"},
            {"id": "t_tecnologico", "categoria": "tecnologico"},
        ])

        service = DashboardService()
        result = await service.get_aluno_dashboard("stu_001")

    assert result.creditos.basico == 4.0
    assert result.creditos.especifico == 3.0
    assert result.creditos.tecnologico == 2.0
    assert result.creditos.total == 9.0

    MockSR.return_value.get.assert_called_once_with("stu_001")
    MockAR.return_value.list_by_student.assert_called_once_with("stu_001")
    MockATR.return_value.list_all.assert_called_once()


# ─── Cycle 4: produções aprovadas e atividades pendentes ────────────────────

@pytest.mark.asyncio
async def test_aluno_dashboard_counts_producoes_and_pending():
    """Conta produções aprovadas (status=aprovado + producao_id) e pendentes (status=enviado)."""
    from backend.app.services.dashboard_service import DashboardService

    student = _make_student()
    activities = [
        {"id": "a1", "status": "aprovado", "producao_id": "prod_1",
         "creditos_concedidos": 6.0, "categoria": "basico"},
        {"id": "a2", "status": "aprovado", "producao_id": "prod_2",
         "creditos_concedidos": 3.0, "categoria": "especifico"},
        {"id": "a3", "status": "enviado", "producao_id": None,
         "creditos_concedidos": 4.0, "categoria": "basico"},
        {"id": "a4", "status": "enviado", "producao_id": None,
         "creditos_concedidos": 2.0, "categoria": "tecnologico"},
        {"id": "a5", "status": "aprovado", "producao_id": None,
         "creditos_concedidos": 4.0, "categoria": "basico"},  # aprovada mas sem produção
    ]

    with (
        patch("backend.app.services.dashboard_service.StudentRepository") as MockSR,
        patch("backend.app.services.dashboard_service.ActivityRepository") as MockAR,
        patch("backend.app.services.dashboard_service.ActivityTypeRepository") as MockATR,
    ):
        MockSR.return_value.get = AsyncMock(return_value=student)
        MockAR.return_value.list_by_student = AsyncMock(return_value=activities)
        MockATR.return_value.list_all = AsyncMock(return_value=[])

        service = DashboardService()
        result = await service.get_aluno_dashboard("stu_001")

    assert result.producoes_aprovadas == 2  # a1, a2 (aprovado + producao_id)
    assert result.atividades_pendentes_validacao == 2  # a3, a4 (enviado)

    MockSR.return_value.get.assert_called_once_with("stu_001")
    MockAR.return_value.list_by_student.assert_called_once_with("stu_001")


# ─── Cycle 5: aluno não encontrado ──────────────────────────────────────────

@pytest.mark.asyncio
async def test_aluno_dashboard_raises_404_if_student_not_found():
    """get_aluno_dashboard lança HTTPException(404) se o aluno não existir."""
    from backend.app.services.dashboard_service import DashboardService

    with (
        patch("backend.app.services.dashboard_service.StudentRepository") as MockSR,
        patch("backend.app.services.dashboard_service.ActivityRepository") as MockAR,
        patch("backend.app.services.dashboard_service.ActivityTypeRepository") as MockATR,
    ):
        MockSR.return_value.get = AsyncMock(return_value=None)

        service = DashboardService()
        with pytest.raises(HTTPException) as exc_info:
            await service.get_aluno_dashboard("stu_inexistente")

    assert exc_info.value.status_code == 404


# ═══════════════════════════════════════════════════════════════════════════════
# ORIENTADOR DASHBOARD
# ═══════════════════════════════════════════════════════════════════════════════

def _make_advisor(overrides: dict | None = None) -> dict:
    """Cria documento advisor para testes."""
    base = {
        "id": "adv_001",
        "uid": "uid_orientador_001",
        "nome": "Prof. Carlos Lima",
        "email": "carlos@test.com",
        "programa_id": "prog_default",
        "ativo": True,
    }
    if overrides:
        base.update(overrides)
    return base


# ─── Cycle 6: tracer bullet orientador ──────────────────────────────────────

@pytest.mark.asyncio
async def test_orientador_dashboard_returns_basic_data():
    """Tracer bullet: get_orientador_dashboard retorna dados básicos."""
    from backend.app.services.dashboard_service import DashboardService
    from backend.app.models.dashboard import OrientadorDashboardResponse

    advisor = _make_advisor()
    students = [
        _make_student({"id": "stu_001", "orientador_id": "adv_001",
                       "situacao_inferida": "regular"}),
        _make_student({"id": "stu_002", "orientador_id": "adv_001",
                       "nome": "João Santos", "situacao_inferida": "em_risco"}),
    ]

    with (
        patch("backend.app.services.dashboard_service.StudentRepository") as MockSR,
        patch("backend.app.services.dashboard_service.ActivityRepository") as MockAR,
        patch("backend.app.services.dashboard_service.ActivityTypeRepository") as MockATR,
        patch("backend.app.services.dashboard_service.AdvisorRepository") as MockAdvR,
    ):
        MockAdvR.return_value.get = AsyncMock(return_value=advisor)
        MockSR.return_value.list_all = AsyncMock(return_value=students)
        MockAR.return_value.list_by_student = AsyncMock(return_value=[])

        service = DashboardService()
        result = await service.get_orientador_dashboard("adv_001")

    assert isinstance(result, OrientadorDashboardResponse)
    assert result.advisor_id == "adv_001"
    assert result.nome == "Prof. Carlos Lima"
    assert result.total_orientandos == 2

    MockAdvR.return_value.get.assert_called_once_with("adv_001")
    MockSR.return_value.list_all.assert_called_once()
    assert MockAR.return_value.list_by_student.call_count == 2


# ─── Cycle 7: contagem por status ───────────────────────────────────────────

@pytest.mark.asyncio
async def test_orientador_dashboard_counts_by_status():
    """Orientandos são contados por situacao_inferida."""
    from backend.app.services.dashboard_service import DashboardService

    advisor = _make_advisor()
    students = [
        _make_student({"id": "s1", "orientador_id": "adv_001",
                       "situacao_inferida": "regular"}),
        _make_student({"id": "s2", "orientador_id": "adv_001",
                       "situacao_inferida": "regular"}),
        _make_student({"id": "s3", "orientador_id": "adv_001",
                       "situacao_inferida": "em_risco"}),
        _make_student({"id": "s4", "orientador_id": "adv_001",
                       "situacao_inferida": "em_fase_de_defesa"}),
    ]

    with (
        patch("backend.app.services.dashboard_service.StudentRepository") as MockSR,
        patch("backend.app.services.dashboard_service.ActivityRepository") as MockAR,
        patch("backend.app.services.dashboard_service.ActivityTypeRepository") as MockATR,
        patch("backend.app.services.dashboard_service.AdvisorRepository") as MockAdvR,
    ):
        MockAdvR.return_value.get = AsyncMock(return_value=advisor)
        MockSR.return_value.list_all = AsyncMock(return_value=students)
        MockAR.return_value.list_by_student = AsyncMock(return_value=[])

        service = DashboardService()
        result = await service.get_orientador_dashboard("adv_001")

    assert result.orientandos_por_status.regular == 2
    assert result.orientandos_por_status.em_risco == 1
    assert result.orientandos_por_status.fase_defesa == 1
    assert result.total_orientandos == 4

    MockAdvR.return_value.get.assert_called_once_with("adv_001")
    MockSR.return_value.list_all.assert_called_once()


# ─── Cycle 8: atividades aguardando parecer ─────────────────────────────────

@pytest.mark.asyncio
async def test_orientador_dashboard_counts_pending_activities():
    """Conta atividades com status=enviado nos orientandos."""
    from backend.app.services.dashboard_service import DashboardService

    advisor = _make_advisor()
    students = [
        _make_student({"id": "s1", "orientador_id": "adv_001"}),
    ]
    activities = [
        {"id": "a1", "status": "enviado"},
        {"id": "a2", "status": "enviado"},
        {"id": "a3", "status": "aprovado"},
    ]

    with (
        patch("backend.app.services.dashboard_service.StudentRepository") as MockSR,
        patch("backend.app.services.dashboard_service.ActivityRepository") as MockAR,
        patch("backend.app.services.dashboard_service.ActivityTypeRepository") as MockATR,
        patch("backend.app.services.dashboard_service.AdvisorRepository") as MockAdvR,
    ):
        MockAdvR.return_value.get = AsyncMock(return_value=advisor)
        MockSR.return_value.list_all = AsyncMock(return_value=students)
        MockAR.return_value.list_by_student = AsyncMock(return_value=activities)

        service = DashboardService()
        result = await service.get_orientador_dashboard("adv_001")

    assert result.atividades_aguardando_parecer == 2
    MockAdvR.return_value.get.assert_called_once_with("adv_001")
    MockAR.return_value.list_by_student.assert_called_once_with("s1")


# ─── Cycle 9: orientador não encontrado ─────────────────────────────────────

@pytest.mark.asyncio
async def test_orientador_dashboard_raises_404_if_not_found():
    """get_orientador_dashboard lança HTTPException(404) se o orientador não existir."""
    from backend.app.services.dashboard_service import DashboardService

    with (
        patch("backend.app.services.dashboard_service.StudentRepository") as MockSR,
        patch("backend.app.services.dashboard_service.ActivityRepository") as MockAR,
        patch("backend.app.services.dashboard_service.ActivityTypeRepository") as MockATR,
        patch("backend.app.services.dashboard_service.AdvisorRepository") as MockAdvR,
    ):
        MockAdvR.return_value.get = AsyncMock(return_value=None)

        service = DashboardService()
        with pytest.raises(HTTPException) as exc_info:
            await service.get_orientador_dashboard("adv_inexistente")

    assert exc_info.value.status_code == 404


# ═══════════════════════════════════════════════════════════════════════════════
# COORDENAÇÃO DASHBOARD
# ═══════════════════════════════════════════════════════════════════════════════

# ─── Cycle 10: tracer bullet coordenação ────────────────────────────────────

@pytest.mark.asyncio
async def test_coord_dashboard_returns_basic_totals():
    """Tracer bullet: get_coordenacao_dashboard retorna totais básicos."""
    from backend.app.services.dashboard_service import DashboardService
    from backend.app.models.dashboard import CoordDashboardResponse

    students = [
        _make_student({"id": "s1", "situacao_inferida": "regular"}),
        _make_student({"id": "s2", "situacao_inferida": "em_risco"}),
        _make_student({"id": "s3", "situacao_inferida": "regular"}),
    ]

    with (
        patch("backend.app.services.dashboard_service.StudentRepository") as MockSR,
        patch("backend.app.services.dashboard_service.ActivityRepository") as MockAR,
        patch("backend.app.services.dashboard_service.ActivityTypeRepository") as MockATR,
        patch("backend.app.services.dashboard_service.AdvisorRepository") as MockAdvR,
        patch("backend.app.services.dashboard_service.FirebaseRepository") as MockFBR,
    ):
        MockSR.return_value.list_all = AsyncMock(return_value=students)
        MockAR.return_value.list_by_student = AsyncMock(return_value=[])
        MockFBR.return_value.list_all = AsyncMock(return_value=[])

        service = DashboardService()
        result = await service.get_coordenacao_dashboard()

    assert isinstance(result, CoordDashboardResponse)
    assert result.programa_id == "prog_default"
    assert result.total_alunos_ativos == 3
    assert result.alunos_por_status.regular == 2
    assert result.alunos_por_status.em_risco == 1

    MockSR.return_value.list_all.assert_called_once()
    assert MockAR.return_value.list_by_student.call_count == 3


# ─── Cycle 11: sem alunos concluídos → tempo_medio = None ──────────────────

@pytest.mark.asyncio
async def test_coord_dashboard_tempo_medio_none_when_no_completed():
    """Quando não há alunos concluídos, tempo_medio_integralizacao_meses = None."""
    from backend.app.services.dashboard_service import DashboardService

    students = [
        _make_student({"id": "s1", "situacao_inferida": "regular"}),
    ]

    with (
        patch("backend.app.services.dashboard_service.StudentRepository") as MockSR,
        patch("backend.app.services.dashboard_service.ActivityRepository") as MockAR,
        patch("backend.app.services.dashboard_service.ActivityTypeRepository") as MockATR,
        patch("backend.app.services.dashboard_service.AdvisorRepository") as MockAdvR,
        patch("backend.app.services.dashboard_service.FirebaseRepository") as MockFBR,
    ):
        MockSR.return_value.list_all = AsyncMock(return_value=students)
        MockAR.return_value.list_by_student = AsyncMock(return_value=[])
        MockFBR.return_value.list_all = AsyncMock(return_value=[])

        service = DashboardService()
        result = await service.get_coordenacao_dashboard()

    assert result.tempo_medio_integralizacao_meses is None


# ─── Cycle 12: atividades aguardando validação (global) ─────────────────────

@pytest.mark.asyncio
async def test_coord_dashboard_counts_global_pending_activities():
    """Conta atividades com status=enviado de todos os alunos."""
    from backend.app.services.dashboard_service import DashboardService

    students = [
        _make_student({"id": "s1"}),
        _make_student({"id": "s2"}),
    ]

    # Mock para retornar atividades diferentes por aluno
    call_count = 0
    async def mock_list_by_student(student_id: str) -> list[dict]:
        nonlocal call_count
        call_count += 1
        if student_id == "s1":
            return [{"id": "a1", "status": "enviado"}, {"id": "a2", "status": "aprovado"}]
        return [{"id": "a3", "status": "enviado"}, {"id": "a4", "status": "enviado"}]

    with (
        patch("backend.app.services.dashboard_service.StudentRepository") as MockSR,
        patch("backend.app.services.dashboard_service.ActivityRepository") as MockAR,
        patch("backend.app.services.dashboard_service.ActivityTypeRepository") as MockATR,
        patch("backend.app.services.dashboard_service.AdvisorRepository") as MockAdvR,
        patch("backend.app.services.dashboard_service.FirebaseRepository") as MockFBR,
    ):
        MockSR.return_value.list_all = AsyncMock(return_value=students)
        MockAR.return_value.list_by_student = AsyncMock(side_effect=mock_list_by_student)
        MockFBR.return_value.list_all = AsyncMock(return_value=[])

        service = DashboardService()
        result = await service.get_coordenacao_dashboard()

    assert result.atividades_aguardando_validacao == 3  # s1: 1, s2: 2


# ─── Cycle 13: auditoria recente ────────────────────────────────────────────

@pytest.mark.asyncio
async def test_coord_dashboard_includes_recent_audit():
    """Auditoria recente traz até 5 itens dos audit_logs."""
    from backend.app.services.dashboard_service import DashboardService

    audit_logs = [
        {"id": "log1", "operacao": "create_student", "usuario_id": "uid_001",
         "timestamp": datetime(2026, 6, 1, tzinfo=timezone.utc)},
        {"id": "log2", "operacao": "update_student", "usuario_id": "uid_002",
         "timestamp": datetime(2026, 6, 2, tzinfo=timezone.utc)},
    ]

    with (
        patch("backend.app.services.dashboard_service.StudentRepository") as MockSR,
        patch("backend.app.services.dashboard_service.ActivityRepository") as MockAR,
        patch("backend.app.services.dashboard_service.ActivityTypeRepository") as MockATR,
        patch("backend.app.services.dashboard_service.AdvisorRepository") as MockAdvR,
        patch("backend.app.services.dashboard_service.FirebaseRepository") as MockFBR,
    ):
        MockSR.return_value.list_all = AsyncMock(return_value=[])
        MockAR.return_value.list_by_student = AsyncMock(return_value=[])
        # Diferenciar instâncias de FirebaseRepository por coleção
        MockFBR.return_value.list_all = AsyncMock(return_value=audit_logs)

        service = DashboardService()
        result = await service.get_coordenacao_dashboard()

    assert len(result.auditoria_recente) == 2
    assert result.auditoria_recente[0].operacao == "update_student"  # mais recente primeiro


# ─── Cycle 14: total concluidos ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_coord_dashboard_counts_total_concluidos():
    """coordenação com N alunos concluídos retorna N, sem alunos retorna 0."""
    from backend.app.services.dashboard_service import DashboardService

    students = [
        _make_student({"id": "s1", "situacao_registrada": "regular"}),
        _make_student({"id": "s2", "situacao_registrada": "concluido"}),
        _make_student({"id": "s3", "situacao_registrada": "concluido"}),
    ]

    with (
        patch("backend.app.services.dashboard_service.StudentRepository") as MockSR,
        patch("backend.app.services.dashboard_service.ActivityRepository") as MockAR,
        patch("backend.app.services.dashboard_service.ActivityTypeRepository") as MockATR,
        patch("backend.app.services.dashboard_service.AdvisorRepository") as MockAdvR,
        patch("backend.app.services.dashboard_service.FirebaseRepository") as MockFBR,
    ):
        MockSR.return_value.list_all = AsyncMock(return_value=students)
        MockAR.return_value.list_by_student = AsyncMock(return_value=[])
        MockFBR.return_value.list_all = AsyncMock(return_value=[])

        service = DashboardService()
        result = await service.get_coordenacao_dashboard()

    assert result.total_concluidos == 2

@pytest.mark.asyncio
async def test_coord_dashboard_counts_total_concluidos_zero():
    """coordenação sem alunos concluídos retorna total_concluidos == 0."""
    from backend.app.services.dashboard_service import DashboardService

    students = [
        _make_student({"id": "s1", "situacao_registrada": "regular"}),
    ]

    with (
        patch("backend.app.services.dashboard_service.StudentRepository") as MockSR,
        patch("backend.app.services.dashboard_service.ActivityRepository") as MockAR,
        patch("backend.app.services.dashboard_service.ActivityTypeRepository") as MockATR,
        patch("backend.app.services.dashboard_service.AdvisorRepository") as MockAdvR,
        patch("backend.app.services.dashboard_service.FirebaseRepository") as MockFBR,
    ):
        MockSR.return_value.list_all = AsyncMock(return_value=students)
        MockAR.return_value.list_by_student = AsyncMock(return_value=[])
        MockFBR.return_value.list_all = AsyncMock(return_value=[])

        service = DashboardService()
        result = await service.get_coordenacao_dashboard()

    assert result.total_concluidos == 0

# ─── Cycle 15: total alunos e total alunos ativos ────────────────────────────

@pytest.mark.asyncio
async def test_coord_dashboard_counts_total_alunos_vs_ativos():
    """total_alunos deve ser a contagem geral sem filtros, e total_alunos_ativos exclui concluidos/desligados."""
    from backend.app.services.dashboard_service import DashboardService

    students = [
        _make_student({"id": "s1", "situacao_registrada": "regular"}),
        _make_student({"id": "s2", "situacao_registrada": "em_risco"}),
        _make_student({"id": "s3", "situacao_registrada": "concluido"}),
        _make_student({"id": "s4", "situacao_registrada": "desligado"}),
    ]

    with (
        patch("backend.app.services.dashboard_service.StudentRepository") as MockSR,
        patch("backend.app.services.dashboard_service.ActivityRepository") as MockAR,
        patch("backend.app.services.dashboard_service.ActivityTypeRepository") as MockATR,
        patch("backend.app.services.dashboard_service.AdvisorRepository") as MockAdvR,
        patch("backend.app.services.dashboard_service.FirebaseRepository") as MockFBR,
    ):
        MockSR.return_value.list_all = AsyncMock(return_value=students)
        MockAR.return_value.list_by_student = AsyncMock(return_value=[])
        MockFBR.return_value.list_all = AsyncMock(return_value=[])

        service = DashboardService()
        result = await service.get_coordenacao_dashboard()

    assert result.total_alunos == 4
    assert result.total_alunos_ativos == 2

