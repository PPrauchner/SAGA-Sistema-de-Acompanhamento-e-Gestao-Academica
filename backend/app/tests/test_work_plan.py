"""Testes do plano de trabalho persistido no Firestore (via FakeFirestore in-process)."""

from datetime import datetime, timezone

import pytest
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.app.api.v1 import work_plan
from backend.app.aspects.alerts import trigger_alerts
from backend.app.aspects.deadline_validation import check_deadlines
from backend.app.core.auth import CurrentUser, get_current_user
from backend.app.repositories.work_plan_repository import WorkPlanRepository
from backend.app.services.inference_service import InferenceService
from backend.app.services.work_plan_service import WorkPlanNotFoundError, WorkPlanService
from backend.app.tests.fake_firestore import FakeFirestore


@pytest.fixture
def fake_db():
    """Patcha o cliente Firestore do repositorio por um fake compartilhado em memoria."""
    fake = FakeFirestore()
    with patch(
        "backend.app.repositories.work_plan_repository.get_firestore_client",
        return_value=fake,
    ), patch(
        "backend.app.aspects.alerts.get_firestore_client",
        return_value=fake,
    ):
        yield fake


def _app(role: str = "orientador", uid: str | None = None) -> FastAPI:
    app = FastAPI()
    app.include_router(work_plan.router, prefix="/api/v1")
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        uid=uid or role,
        role=role,
        programa_id="prog_default",
        email=f"{role}@example.com",
    )
    return app


def _client(role: str = "orientador") -> TestClient:
    return TestClient(_app(role))


_FUTURE = "2027-06-01T00:00:00Z"
_PAST = "2025-01-01T00:00:00Z"


def _build_plan_via_api(student_id: str = "aluno_real") -> dict[str, str]:
    """Cria plano -> etapa -> duas tasks pela API (orientador) e devolve os ids."""
    client = _client("orientador")
    plan_id = client.post(
        f"/api/v1/work-plan/{student_id}",
        json={"titulo": "Plano real", "data_inicio": _PAST, "data_fim_prevista": _FUTURE},
    ).json()["plan_id"]
    stage_id = client.post(
        f"/api/v1/work-plan/{plan_id}/stages",
        json={"nome": "Desenvolvimento", "ordem": 1, "data_inicio": _PAST, "data_fim": _FUTURE},
    ).json()["stage_id"]
    t1 = client.post(
        f"/api/v1/stages/{stage_id}/tasks",
        json={"titulo": "Tarefa 1", "descricao": "", "prazo": _FUTURE, "prioridade": "alta"},
    ).json()["task_id"]
    t2 = client.post(
        f"/api/v1/stages/{stage_id}/tasks",
        json={"titulo": "Tarefa 2", "descricao": "", "prazo": _FUTURE, "prioridade": "media"},
    ).json()["task_id"]
    return {"student_id": student_id, "plan_id": plan_id, "stage_id": stage_id, "t1": t1, "t2": t2}


async def _seed_plan_async(repo: WorkPlanRepository, student_id: str) -> dict[str, str]:
    """Cria plano -> etapa -> task diretamente pelo repositorio (para testes async)."""
    plan_id = await repo.create_plan(
        student_id,
        {
            "titulo": "Plano real",
            "data_inicio": datetime(2025, 1, 1, tzinfo=timezone.utc),
            "data_fim_prevista": datetime(2027, 6, 1, tzinfo=timezone.utc),
            "descricao": None,
        },
    )
    stage_id = await repo.create_stage(
        plan_id,
        {
            "nome": "Desenvolvimento",
            "ordem": 1,
            "data_inicio": datetime(2025, 1, 1, tzinfo=timezone.utc),
            "data_fim": datetime(2027, 6, 1, tzinfo=timezone.utc),
        },
    )
    task_id = await repo.create_task(
        stage_id,
        {
            "titulo": "Tarefa 1",
            "descricao": "",
            "prazo": datetime(2027, 6, 1, tzinfo=timezone.utc),
            "prioridade": "alta",
        },
    )
    return {"student_id": student_id, "plan_id": plan_id, "stage_id": stage_id, "task_id": task_id}


def test_get_work_plan_returns_real_stages_and_tasks(fake_db) -> None:
    ids = _build_plan_via_api("aluno_real")

    response = _client().get(f"/api/v1/work-plan/{ids['student_id']}")

    assert response.status_code == 200
    body = response.json()
    assert body["student_id"] == "aluno_real"
    assert body["plan_id"] == ids["plan_id"]
    assert body["stages"]
    assert body["stages"][0]["tasks"]


def test_get_work_plan_missing_returns_404(fake_db) -> None:
    response = _client().get("/api/v1/work-plan/aluno_sem_plano")

    assert response.status_code == 404


def test_progress_update_recalculates_progress_and_notifies(fake_db) -> None:
    ids = _build_plan_via_api("aluno_real")

    response = _client("aluno").post(
        f"/api/v1/tasks/{ids['t1']}/updates",
        json={"conteudo": "Tarefa finalizada", "percentual": 100},
        headers={"X-User-Id": "aluno_real", "X-User-Name": "Aluno Real", "X-User-Role": "aluno"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["notificacao_enviada_ao_orientador"] is True
    assert body["progresso_percentual"] > 0


def test_progress_update_to_100_persists_plano_concluido(fake_db) -> None:
    """Regressão M1: concluir a última task não-defesa via progresso 100% grava plano_concluido."""
    ids = _build_plan_via_api("aluno_real")
    headers = {"X-User-Id": "aluno_real", "X-User-Name": "Aluno Real", "X-User-Role": "aluno"}

    for task_id in (ids["t1"], ids["t2"]):
        response = _client("aluno").post(
            f"/api/v1/tasks/{task_id}/updates",
            json={"conteudo": "Concluída", "percentual": 100},
            headers=headers,
        )
        assert response.status_code == 201

    plan = _client().get(f"/api/v1/work-plan/{ids['student_id']}").json()
    assert plan["plano_concluido"] is True
    assert plan["fato_plano_concluido"] == "plano_concluido(aluno_real)"


def test_progress_update_uses_deadline_and_alert_aspects() -> None:
    wrapped = work_plan.add_progress_update

    assert hasattr(wrapped, "__wrapped__")
    assert check_deadlines.__name__ == "check_deadlines"
    assert trigger_alerts.__name__ == "trigger_alerts"


async def test_progress_update_creates_standard_notification_document(fake_db) -> None:
    repo = WorkPlanRepository()
    ids = await _seed_plan_async(repo, "aluno_real")

    app = _app("aluno", uid="aluno_real")
    with TestClient(app) as client:
        response = client.post(
            f"/api/v1/tasks/{ids['task_id']}/updates",
            json={"conteudo": "Analise iniciada", "percentual": 25},
            headers={"X-User-Id": "aluno_real", "X-User-Name": "Aluno Real", "X-User-Role": "aluno"},
        )

    assert response.status_code == 201
    notifications = await repo.list_notifications()
    notification = notifications[-1]

    assert response.json()["notificacao_enviada_ao_orientador"] is True
    assert {
        "tipo",
        "titulo",
        "mensagem",
        "destinatario_id",
        "entidade_id",
        "lida",
        "timestamp",
    }.issubset(notification)
    assert notification["tipo"] == "progresso_task"
    assert notification["destinatario_id"] == "orientador"
    assert notification["lida"] is False


def test_progress_update_requires_aluno_role(fake_db) -> None:
    response = _client("orientador").post(
        "/api/v1/tasks/task_qualquer/updates",
        json={"conteudo": "Tentativa pelo orientador", "percentual": 75},
        headers={"X-User-Id": "orientador", "X-User-Name": "Orientador", "X-User-Role": "orientador"},
    )

    assert response.status_code == 403


def test_work_plan_mutations_require_orientador_role(fake_db) -> None:
    app = _app()
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        uid="aluno_real",
        role="aluno",
        programa_id="prog_default",
        email="aluno@example.com",
    )
    response = TestClient(app).post(
        "/api/v1/work-plan/aluno_bloqueado",
        json={
            "titulo": "Plano bloqueado",
            "data_inicio": "2026-01-01T00:00:00Z",
            "data_fim_prevista": "2026-12-01T00:00:00Z",
        },
    )

    assert response.status_code == 403


def test_work_plan_mutations_allow_coordenacao_role(fake_db) -> None:
    response = _client("coordenacao").post(
        "/api/v1/work-plan/aluno_coord",
        json={
            "titulo": "Plano da coordenacao",
            "data_inicio": "2026-01-01T00:00:00Z",
            "data_fim_prevista": "2026-12-01T00:00:00Z",
        },
    )

    assert response.status_code == 201
    assert response.json()["plan_id"].startswith("aluno_coord~")


def test_plan_concluded_fact_available_when_non_defense_tasks_done(fake_db) -> None:
    client = _client()
    plan_id = client.post(
        "/api/v1/work-plan/aluno_issue_44",
        json={"titulo": "Plano Issue 44", "data_inicio": _PAST, "data_fim_prevista": _FUTURE},
    ).json()["plan_id"]
    stage_id = client.post(
        f"/api/v1/work-plan/{plan_id}/stages",
        json={"nome": "Escrita", "ordem": 1, "data_inicio": _PAST, "data_fim": _FUTURE},
    ).json()["stage_id"]
    task_id = client.post(
        f"/api/v1/stages/{stage_id}/tasks",
        json={"titulo": "Capitulo final", "descricao": "", "prazo": _FUTURE, "prioridade": "alta"},
    ).json()["task_id"]

    status_response = client.patch(f"/api/v1/tasks/{task_id}/status", json={"status": "concluido"})
    fact_response = client.get("/api/v1/work-plan/aluno_issue_44/facts/plano-concluido")

    assert status_response.status_code == 200
    assert status_response.json()["plano_concluido"] is True
    assert fact_response.json() == {
        "student_id": "aluno_issue_44",
        "plano_concluido": True,
        "fato": "plano_concluido(aluno_issue_44)",
    }


def test_create_read_update_roundtrip_persists(fake_db) -> None:
    ids = _build_plan_via_api("aluno_persist")
    client = _client()

    patch_response = client.patch(f"/api/v1/tasks/{ids['t1']}/status", json={"status": "concluido"})
    assert patch_response.status_code == 200

    body = client.get("/api/v1/work-plan/aluno_persist").json()
    tasks = {t["task_id"]: t for stage in body["stages"] for t in stage["tasks"]}
    assert tasks[ids["t1"]]["status"] == "concluido"
    assert tasks[ids["t2"]]["status"] == "pendente"
    assert body["progresso_percentual"] == 50.0


async def test_dashboard_source_reflects_real_progress(fake_db) -> None:
    repo = WorkPlanRepository()
    ids = await _seed_plan_async(repo, "aluno_dash")
    await repo.update_task(ids["task_id"], {"status": "concluido", "progresso_percentual": 100.0})

    tasks = await repo.get_all_tasks_for_student("aluno_dash")

    assert len(tasks) == 1
    assert tasks[0]["status"] == "concluido"
    assert {"id", "status", "titulo", "prazo"}.issubset(tasks[0])


async def test_get_plan_tasks_compatible_with_rl01_plan_fact(fake_db) -> None:
    repo = WorkPlanRepository()
    ids = await _seed_plan_async(repo, "aluno_apto")
    await repo.update_task(ids["task_id"], {"status": "concluido", "progresso_percentual": 100.0})

    tasks = await repo.get_plan_tasks("aluno_apto")

    assert tasks
    assert {"id", "is_defesa", "concluida"}.issubset(tasks[0])
    assert InferenceService(repo)._is_plano_concluido(tasks) is True


async def _seed_stage_with_tasks(
    repo: WorkPlanRepository, student_id: str, nome: str, count: int
) -> tuple[str, str, list[str]]:
    """Cria plano -> etapa `nome` -> `count` tasks e devolve (plan_id, stage_id, task_ids)."""
    plan_id = await repo.create_plan(
        student_id,
        {
            "titulo": "Plano real",
            "data_inicio": datetime(2025, 1, 1, tzinfo=timezone.utc),
            "data_fim_prevista": datetime(2027, 6, 1, tzinfo=timezone.utc),
            "descricao": None,
        },
    )
    stage_id = await repo.create_stage(
        plan_id,
        {
            "nome": nome,
            "ordem": 1,
            "data_inicio": datetime(2025, 1, 1, tzinfo=timezone.utc),
            "data_fim": datetime(2027, 6, 1, tzinfo=timezone.utc),
        },
    )
    task_ids = [
        await repo.create_task(
            stage_id,
            {
                "titulo": f"Tarefa {i}",
                "descricao": "",
                "prazo": datetime(2027, 6, 1, tzinfo=timezone.utc),
                "prioridade": "media",
            },
        )
        for i in range(count)
    ]
    return plan_id, stage_id, task_ids


async def test_delete_task_recomputes_stage_progress_and_plan_fact(fake_db) -> None:
    """Remover uma task recomputa o progresso da etapa e o fato plano_concluido (RL01)."""
    repo = WorkPlanRepository()
    service = WorkPlanService(repo)
    _, _, (t1, t2) = await _seed_stage_with_tasks(repo, "aluno_del", "Desenvolvimento", 2)
    await repo.update_task(t1, {"status": "concluido", "progresso_percentual": 100.0})

    before = await repo.get_plan("aluno_del")
    assert before["stages"][0]["progresso_percentual"] == 50.0  # media (100 + 0) / 2

    await service.delete_task(t2)

    after = await repo.get_plan("aluno_del")
    stage = after["stages"][0]
    assert len(stage["tasks"]) == 1
    assert stage["progresso_percentual"] == 100.0
    assert stage["status"] == "concluido"
    assert "plano_concluido(aluno_del)" in after["facts"]


async def test_delete_defense_task_does_not_change_plano_concluido(fake_db) -> None:
    """Excluir task de defesa nao altera plano_concluido — RL01 so olha tasks nao-defesa."""
    repo = WorkPlanRepository()
    service = WorkPlanService(repo)
    plan_id = await repo.create_plan(
        "aluno_rl01",
        {
            "titulo": "Plano",
            "data_inicio": datetime(2025, 1, 1, tzinfo=timezone.utc),
            "data_fim_prevista": datetime(2027, 6, 1, tzinfo=timezone.utc),
            "descricao": None,
        },
    )
    escrita = await repo.create_stage(
        plan_id,
        {"nome": "Escrita", "ordem": 1, "data_inicio": datetime(2025, 1, 1, tzinfo=timezone.utc), "data_fim": datetime(2027, 6, 1, tzinfo=timezone.utc)},
    )
    t_escrita = await repo.create_task(
        escrita,
        {"titulo": "Capitulo", "descricao": "", "prazo": datetime(2027, 6, 1, tzinfo=timezone.utc), "prioridade": "alta"},
    )
    defesa = await repo.create_stage(
        plan_id,
        {"nome": "defesa", "ordem": 2, "data_inicio": datetime(2025, 1, 1, tzinfo=timezone.utc), "data_fim": datetime(2027, 6, 1, tzinfo=timezone.utc)},
    )
    t_defesa = await repo.create_task(
        defesa,
        {"titulo": "Agendar banca", "descricao": "", "prazo": datetime(2027, 6, 1, tzinfo=timezone.utc), "prioridade": "media"},
    )
    await service.update_task_status(t_escrita, "concluido")

    before = await repo.get_plan("aluno_rl01")
    assert "plano_concluido(aluno_rl01)" in before["facts"]  # defesa pendente nao bloqueia

    await service.delete_task(t_defesa)

    after = await repo.get_plan("aluno_rl01")
    assert "plano_concluido(aluno_rl01)" in after["facts"]  # inalterado pela exclusao da defesa


async def test_delete_all_tasks_leaves_stage_not_concluido(fake_db) -> None:
    """Remover todas as tasks nao marca a etapa como concluida e limpa plano_concluido."""
    repo = WorkPlanRepository()
    service = WorkPlanService(repo)
    _, _, (t1, t2) = await _seed_stage_with_tasks(repo, "aluno_empty", "Desenvolvimento", 2)
    await service.update_task_status(t1, "concluido")
    await service.update_task_status(t2, "concluido")

    concluded = await repo.get_plan("aluno_empty")
    assert concluded["stages"][0]["status"] == "concluido"
    assert "plano_concluido(aluno_empty)" in concluded["facts"]

    await service.delete_task(t1)
    await service.delete_task(t2)

    after = await repo.get_plan("aluno_empty")
    stage = after["stages"][0]
    assert stage["tasks"] == []
    assert stage["status"] != "concluido"
    assert stage["progresso_percentual"] == 0.0
    assert "plano_concluido(aluno_empty)" not in after["facts"]


async def test_delete_missing_task_raises_not_found(fake_db) -> None:
    repo = WorkPlanRepository()
    service = WorkPlanService(repo)
    with pytest.raises(WorkPlanNotFoundError):
        await service.delete_task("inexistente~plan~stage~task")
