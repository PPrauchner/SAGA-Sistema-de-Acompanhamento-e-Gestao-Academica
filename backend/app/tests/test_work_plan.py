from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.app.api.v1 import work_plan
from backend.app.aspects.alerts import trigger_alerts
from backend.app.aspects.deadline_validation import check_deadlines
from backend.app.core.auth import CurrentUser, get_current_user
from backend.app.repositories.work_plan_repository import WorkPlanRepository
from backend.app.services.inference_service import InferenceService


def _app() -> FastAPI:
    app = FastAPI()
    app.include_router(work_plan.router, prefix="/api/v1")
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        uid="orientador",
        role="orientador",
        programa_id="prog_default",
        email="orientador@example.com",
    )
    return app


def _client() -> TestClient:
    app = _app()
    return TestClient(app)


def test_get_work_plan_returns_real_stages_and_tasks() -> None:
    response = _client().get("/api/v1/work-plan/aluno_regular")

    assert response.status_code == 200
    body = response.json()
    assert body["student_id"] == "aluno_regular"
    assert body["plan_id"] == "plan_aluno_regular"
    assert body["stages"]
    assert body["stages"][0]["tasks"]


def test_progress_update_recalculates_progress_and_notifies() -> None:
    response = _client().post(
        "/api/v1/tasks/task_dev_2/updates",
        json={"conteudo": "Experimentos finalizados", "percentual": 100},
        headers={"X-User-Id": "aluno_regular", "X-User-Name": "Rita Regular", "X-User-Role": "aluno"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["notificacao_enviada_ao_orientador"] is True
    assert body["progresso_percentual"] > 0


def test_progress_update_uses_deadline_and_alert_aspects() -> None:
    wrapped = work_plan.add_progress_update

    assert hasattr(wrapped, "__wrapped__")
    assert check_deadlines.__name__ == "check_deadlines"
    assert trigger_alerts.__name__ == "trigger_alerts"


async def test_progress_update_creates_standard_notification_document() -> None:
    app = _app()
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/tasks/task_dev_3/updates",
            json={"conteudo": "Analise iniciada", "percentual": 25},
            headers={"X-User-Id": "aluno_regular", "X-User-Name": "Rita Regular", "X-User-Role": "aluno"},
        )

    assert response.status_code == 201
    repo = WorkPlanRepository(app.state.work_plan_store)
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


def test_work_plan_mutations_require_orientador_role() -> None:
    app = _app()
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        uid="aluno_regular",
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


def test_plan_concluded_fact_available_when_non_defense_tasks_done() -> None:
    client = _client()
    response = client.post(
        "/api/v1/work-plan/aluno_issue_44",
        json={
            "titulo": "Plano Issue 44",
            "data_inicio": "2026-01-01T00:00:00Z",
            "data_fim_prevista": "2026-12-01T00:00:00Z",
        },
    )
    plan_id = response.json()["plan_id"]
    stage_response = client.post(
        f"/api/v1/work-plan/{plan_id}/stages",
        json={
            "nome": "Escrita",
            "ordem": 1,
            "data_inicio": "2026-01-01T00:00:00Z",
            "data_fim": "2026-06-01T00:00:00Z",
        },
    )
    stage_id = stage_response.json()["stage_id"]
    task_response = client.post(
        f"/api/v1/stages/{stage_id}/tasks",
        json={"titulo": "Capitulo final", "descricao": "", "prazo": "2026-05-01T00:00:00Z", "prioridade": "alta"},
    )
    task_id = task_response.json()["task_id"]

    status_response = client.patch(f"/api/v1/tasks/{task_id}/status", json={"status": "concluido"})
    fact_response = client.get("/api/v1/work-plan/aluno_issue_44/facts/plano-concluido")

    assert status_response.status_code == 200
    assert status_response.json()["plano_concluido"] is True
    assert fact_response.json() == {
        "student_id": "aluno_issue_44",
        "plano_concluido": True,
        "fato": "plano_concluido(aluno_issue_44)",
    }


async def test_work_plan_tasks_are_compatible_with_rl01_plan_fact() -> None:
    repo = WorkPlanRepository()
    tasks = await repo.get_plan_tasks("aluno_apto")

    assert tasks
    assert {"id", "is_defesa", "concluida"}.issubset(tasks[0])
    assert InferenceService(repo)._is_plano_concluido(tasks) is True
