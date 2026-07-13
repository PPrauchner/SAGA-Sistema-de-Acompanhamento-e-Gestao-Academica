"""
Testes do mapeamento de InferenceRepository ao contrato InferenceDataSource (issue #256).

Cobre a carga real de atividades aprovadas (juntando activity_types para grupo/tipo_ativo,
com override de creditos_concedidos e filtro por status), a delegação das tasks do plano ao
WorkPlanRepository e a marcação bibliografica das produções aprovadas.
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

from backend.app.models.program_config import DEFAULT_PROGRAM_CREDIT_CONFIG
from backend.app.repositories import firebase_repository
from backend.app.repositories.inference_repository import InferenceRepository
from backend.app.tests.fake_firestore import FakeFirestore


@pytest.fixture
def fake_db(monkeypatch: pytest.MonkeyPatch) -> FakeFirestore:
    db = FakeFirestore()
    monkeypatch.setattr(firebase_repository, "get_firestore_client", lambda: db)
    return db


def _seed_types(db: FakeFirestore) -> None:
    db.collection("activity_types").document("tb").set({"categoria": "basico", "ativo": True})
    db.collection("activity_types").document("te").set({"categoria": "especifico", "ativo": True})
    db.collection("activity_types").document("tt").set({"categoria": "tecnologico", "ativo": False})


def _activities(db: FakeFirestore, student_id: str):
    return db.collection("students").document(student_id).collection("activities")


async def test_get_approved_activities_mapeia_grupo_creditos_e_tipo(fake_db: FakeFirestore) -> None:
    _seed_types(fake_db)
    _activities(fake_db, "s1").document("a1").set(
        {
            "tipo_id": "tb",
            "status": "aprovado",
            "creditos_gerados": 12,
            "creditos_concedidos": None,
            "comprovante_url": "url/b",
            "data_realizacao": datetime(2022, 6, 1, tzinfo=timezone.utc),
        }
    )

    result = await InferenceRepository().get_approved_activities("s1")

    assert result == [
        {
            "id": "a1",
            "grupo": "basico",
            "creditos": 12.0,
            "comprovante": "url/b",
            "tipo_ativo": True,
            "data": "2022-06-01",
        }
    ]


async def test_get_approved_activities_usa_creditos_concedidos_quando_presente(
    fake_db: FakeFirestore,
) -> None:
    _seed_types(fake_db)
    _activities(fake_db, "s1").document("a2").set(
        {
            "tipo_id": "te",
            "status": "aprovado",
            "creditos_gerados": 8,
            "creditos_concedidos": 10,
            "comprovante_url": None,
            "data_realizacao": None,
        }
    )

    result = await InferenceRepository().get_approved_activities("s1")

    assert result[0]["creditos"] == 10.0
    assert result[0]["grupo"] == "especifico"


async def test_get_approved_activities_ignora_nao_aprovadas(fake_db: FakeFirestore) -> None:
    _seed_types(fake_db)
    _activities(fake_db, "s1").document("a1").set({"tipo_id": "tb", "status": "aprovado", "creditos_gerados": 12})
    _activities(fake_db, "s1").document("a3").set({"tipo_id": "tt", "status": "enviado", "creditos_gerados": 3})

    result = await InferenceRepository().get_approved_activities("s1")

    assert [a["id"] for a in result] == ["a1"]


async def test_get_plan_tasks_delega_ao_work_plan(monkeypatch: pytest.MonkeyPatch) -> None:
    repo = InferenceRepository()
    tasks = [{"id": "t1", "is_defesa": False, "concluida": True}]
    monkeypatch.setattr(repo._work_plan, "get_plan_tasks", AsyncMock(return_value=tasks))

    assert await repo.get_plan_tasks("s1") == tasks


async def test_get_program_inexistente_usa_defaults_canonicos(monkeypatch: pytest.MonkeyPatch) -> None:
    repo = InferenceRepository()
    monkeypatch.setattr(repo._programs, "get", AsyncMock(return_value=None))

    result = await repo.get_program("prog_default")

    assert result == {
        "id": "prog_default",
        **DEFAULT_PROGRAM_CREDIT_CONFIG,
        "max_prorrogacoes": 1,
        "meses_ate_qualificacao": 12,
    }
    assert "min_creditos_total" not in result


async def test_get_program_parcial_usa_default_apenas_da_chave_ausente(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = InferenceRepository()
    monkeypatch.setattr(
        repo._programs,
        "get",
        AsyncMock(
            return_value={
                "creditos_grupo_basico_min": 14,
                "creditos_grupo_especifico_min": 9,
                "creditos_total_min": 30,
                "max_prorrogacoes": 3,
                "meses_ate_qualificacao": 18,
            }
        ),
    )

    result = await repo.get_program("prog_custom")

    assert result["creditos_grupo_basico_min"] == 14
    assert result["creditos_grupo_especifico_min"] == 9
    assert (
        result["creditos_grupo_tecnologico_max"]
        == DEFAULT_PROGRAM_CREDIT_CONFIG["creditos_grupo_tecnologico_max"]
    )
    assert result["creditos_total_min"] == 30
    assert result["max_prorrogacoes"] == 3
    assert result["meses_ate_qualificacao"] == 18


async def test_get_program_preserva_creditos_configurados(monkeypatch: pytest.MonkeyPatch) -> None:
    repo = InferenceRepository()
    configured = {
        "creditos_grupo_basico_min": 16,
        "creditos_grupo_especifico_min": 11,
        "creditos_grupo_tecnologico_max": 6,
        "creditos_total_min": 35,
    }
    monkeypatch.setattr(repo._programs, "get", AsyncMock(return_value=configured))

    result = await repo.get_program("prog_custom")

    for key, value in configured.items():
        assert result[key] == value


async def test_get_approved_productions_marca_bibliografica(monkeypatch: pytest.MonkeyPatch) -> None:
    repo = InferenceRepository()
    monkeypatch.setattr(repo._students, "get", AsyncMock(return_value={"programa_id": "prog_default"}))
    monkeypatch.setattr(
        repo._activities,
        "list_by_student",
        AsyncMock(return_value=[{"producao_id": "p1", "status": "aprovado", "data_realizacao": None}]),
    )
    monkeypatch.setattr(repo._vehicles, "list_levels", AsyncMock(return_value=[{"id": "v1", "nivel": "A1"}]))
    monkeypatch.setattr(
        repo._productions,
        "get",
        AsyncMock(return_value={"id": "p1", "veiculo_id": "v1", "pontuacao_base": 10, "status_publicacao": "publicado"}),
    )

    result = await repo.get_approved_productions("s1")

    assert result[0]["bibliografica"] is True
    assert result[0]["nivel"] == "A1"
