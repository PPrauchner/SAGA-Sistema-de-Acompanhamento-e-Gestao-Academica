"""
Ownership do plano de trabalho / kanban (issue #248).

`@requires_role` faz o gate grosso de papel; `@check_work_plan_ownership` valida a
relação de orientação. O direito de editar vem de ser o orientador do aluno
(ownership), não do papel — logo a coordenação é read-only e um coordenador que
também orienta o aluno edita via a relação de orientação.

Cobre cada papel + o caso de papel duplo (coordenador-orientador) + coorientador,
isolando a verificação de ownership dos demais aspectos (que tocariam o Firestore).
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from backend.app.aspects import aspect_config
from backend.app.api.v1.work_plan import _get_service
from backend.app.core.auth import CurrentUser, get_current_user
from backend.app.main import app
from backend.app.models.work_plan import (
    CreateStageResponse,
    TaskStatusResponse,
    WorkPlanFull,
)

_STUDENT_ID = "stu1"
_PLAN_ID = "stu1~plan1"
_TASK_ID = "stu1~plan1~stage1~task1"

_STAGE_CREATE = {
    "nome": "revisao",
    "ordem": 1,
    "data_inicio": "2026-01-01T00:00:00Z",
    "data_fim": "2026-02-01T00:00:00Z",
}
_TASK_STATUS = {"status": "em_andamento"}

# Aluno dono = uid-aluno; orientador = adv-A; coorientador = adv-B.
_STUDENT_DOC: dict[str, Any] = {
    "id": _STUDENT_ID,
    "uid": "uid-aluno",
    "orientador_id": "adv-A",
    "coorientador_id": "adv-B",
    "programa_id": "prog",
}

# uid -> docs devolvidos por advisors.query(uid). Coordenação pura e alunos não
# têm documento em advisors/.
_ADVISORS_BY_UID: dict[str, list[dict[str, Any]]] = {
    "uid-orientador-A": [{"id": "adv-A", "uid": "uid-orientador-A"}],
    "uid-coorientador-B": [{"id": "adv-B", "uid": "uid-coorientador-B"}],
    "uid-orientador-X": [{"id": "adv-X", "uid": "uid-orientador-X"}],
    "uid-coord-adv": [{"id": "adv-A", "uid": "uid-coord-adv"}],
}


class _FakeWorkPlanService:
    """Service falso: o teste valida a autorização, não a lógica de negócio."""

    async def get_plan(self, student_id: str) -> WorkPlanFull:
        return WorkPlanFull(
            plan_id=_PLAN_ID,
            student_id=student_id,
            titulo="Plano",
            data_inicio="2026-01-01T00:00:00Z",
            data_fim_prevista="2026-06-01T00:00:00Z",
        )

    async def create_stage(self, plan_id: str, payload: Any) -> CreateStageResponse:
        return CreateStageResponse(stage_id=f"{plan_id}~stageN")

    async def update_task_status(self, task_id: str, status: str) -> TaskStatusResponse:
        return TaskStatusResponse(message="Status atualizado")

    async def delete_task(self, task_id: str) -> dict[str, str]:
        return {"message": "Task removida"}


def _override_user(uid: str, role: str) -> None:
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        uid=uid, role=role, programa_id="prog", email=f"{uid}@saga.test"
    )


def _patch_repos(monkeypatch: pytest.MonkeyPatch) -> None:
    def _query(filters: list[tuple[str, str, str]]) -> list[dict[str, Any]]:
        uid = filters[0][2]
        return _ADVISORS_BY_UID.get(uid, [])

    def factory(collection: str) -> AsyncMock:
        repo = AsyncMock()
        if collection == "students":
            repo.get.return_value = _STUDENT_DOC
        elif collection == "advisors":
            repo.query.side_effect = _query
        return repo

    monkeypatch.setattr("backend.app.aspects.ownership.FirebaseRepository", factory)


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    app.dependency_overrides[_get_service] = lambda: _FakeWorkPlanService()
    monkeypatch.setattr(aspect_config, "AUDIT_ENABLED", False)
    monkeypatch.setattr(aspect_config, "HISTORY_ENABLED", False)
    monkeypatch.setattr(aspect_config, "DEADLINE_VALIDATION_ENABLED", False)
    monkeypatch.setattr(aspect_config, "ALERTS_ENABLED", False)
    _patch_repos(monkeypatch)
    yield TestClient(app)
    app.dependency_overrides.clear()


# --------------------------------------------------------------------- leitura

_READ_CASES = [
    pytest.param("uid-aluno", "aluno", 200, id="aluno-dono"),
    pytest.param("uid-aluno-x", "aluno", 403, id="aluno-outro"),
    pytest.param("uid-orientador-A", "orientador", 200, id="orientador-do-aluno"),
    pytest.param("uid-orientador-X", "orientador", 403, id="orientador-de-outro"),
    pytest.param("uid-coord-pure", "coordenacao", 200, id="coordenacao-read-only"),
    pytest.param("uid-coorientador-B", "orientador", 200, id="coorientador"),
]


@pytest.mark.parametrize("uid, role, expected", _READ_CASES)
def test_read_ownership(client: TestClient, uid: str, role: str, expected: int) -> None:
    _override_user(uid, role)
    response = client.get(f"/api/v1/work-plan/{_STUDENT_ID}")
    assert response.status_code == expected


# ---------------------------------------------------------------------- edição

_EDIT_CASES = [
    pytest.param("uid-orientador-A", "orientador", 201, id="orientador-do-aluno"),
    pytest.param("uid-orientador-X", "orientador", 403, id="orientador-de-outro"),
    pytest.param("uid-coord-pure", "coordenacao", 403, id="coordenacao-read-only"),
    pytest.param("uid-coord-adv", "coordenacao", 201, id="coordenador-que-orienta"),
    pytest.param("uid-coorientador-B", "orientador", 201, id="coorientador"),
]


@pytest.mark.parametrize("uid, role, expected", _EDIT_CASES)
def test_edit_ownership(client: TestClient, uid: str, role: str, expected: int) -> None:
    _override_user(uid, role)
    response = client.post(f"/api/v1/work-plan/{_PLAN_ID}/stages", json=_STAGE_CREATE)
    assert response.status_code == expected


def test_aluno_nao_cria_etapa(client: TestClient) -> None:
    # Aluno é barrado já no gate de papel — não cria etapas/tasks.
    _override_user("uid-aluno", "aluno")
    response = client.post(f"/api/v1/work-plan/{_PLAN_ID}/stages", json=_STAGE_CREATE)
    assert response.status_code == 403


# --------------------------------------------------------- mover status (kanban)

_STATUS_CASES = [
    pytest.param("uid-aluno", "aluno", 200, id="aluno-dono-move-status"),
    pytest.param("uid-aluno-x", "aluno", 403, id="aluno-outro"),
    pytest.param("uid-orientador-A", "orientador", 200, id="orientador-do-aluno"),
    pytest.param("uid-coord-pure", "coordenacao", 403, id="coordenacao-read-only"),
    pytest.param("uid-coord-adv", "coordenacao", 200, id="coordenador-que-orienta"),
]


@pytest.mark.parametrize("uid, role, expected", _STATUS_CASES)
def test_status_ownership(client: TestClient, uid: str, role: str, expected: int) -> None:
    _override_user(uid, role)
    response = client.patch(f"/api/v1/tasks/{_TASK_ID}/status", json=_TASK_STATUS)
    assert response.status_code == expected


# ------------------------------------------------------------ remover task (edit)

# Remover task exige ownership "edit": so orientador/coorientador do aluno; aluno e
# barrado ja no gate de papel; coordenacao sem vinculo de orientacao e read-only.
_DELETE_CASES = [
    pytest.param("uid-orientador-A", "orientador", 200, id="orientador-do-aluno"),
    pytest.param("uid-orientador-X", "orientador", 403, id="orientador-de-outro"),
    pytest.param("uid-coord-pure", "coordenacao", 403, id="coordenacao-read-only"),
    pytest.param("uid-coord-adv", "coordenacao", 200, id="coordenador-que-orienta"),
    pytest.param("uid-coorientador-B", "orientador", 200, id="coorientador"),
    pytest.param("uid-aluno", "aluno", 403, id="aluno-barrado"),
]


@pytest.mark.parametrize("uid, role, expected", _DELETE_CASES)
def test_delete_ownership(client: TestClient, uid: str, role: str, expected: int) -> None:
    _override_user(uid, role)
    response = client.delete(f"/api/v1/tasks/{_TASK_ID}")
    assert response.status_code == expected
