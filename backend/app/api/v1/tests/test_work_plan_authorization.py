"""
Regressão de autorização do endpoint POST /tasks/{id}/updates (plano de trabalho).

Este endpoint declara tanto `actor: ActorContext` (derivado de headers) quanto
`user: CurrentUser` (do JWT), ambos expondo `role`/`uid`. Antes da correção, o
`@requires_role("aluno")` lia o primeiro objeto com `role`/`uid` — o `actor`
controlado por header — em vez da identidade autenticada. Consequências:

- um aluno legítimo (JWT) sem o header era barrado com 403 (actor.role="system");
- o header podia tentar forjar o papel.

Estes testes fixam o contrato: o papel verificado vem do JWT, e o header não
escala nem rebaixa o acesso.
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
from backend.app.models.work_plan import ProgressUpdateCreated

_PROGRESS_UPDATE = {"conteudo": "avancei", "percentual": 50.0}


class _FakeWorkPlanService:
    calls: list[str] = []

    async def add_progress_update(self, task_id: str, payload: Any, actor: Any) -> ProgressUpdateCreated:
        _FakeWorkPlanService.calls.append(task_id)
        return ProgressUpdateCreated(
            update_id="upd1",
            alerta_prazo=False,
            notificacao_enviada_ao_orientador=False,
            progresso_percentual=payload.percentual,
        )


def _override_user(role: str) -> None:
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        uid=f"uid-{role}", role=role, programa_id="prog", email=f"{role}@saga.test"
    )


def _patch_ownership_repo(monkeypatch: pytest.MonkeyPatch) -> None:
    """Faz o aluno legítimo (uid-aluno) ser o dono da task no @check_work_plan_ownership."""

    def factory(collection: str) -> AsyncMock:
        repo = AsyncMock()
        if collection == "students":
            repo.get.return_value = {"uid": "uid-aluno"}
        return repo

    monkeypatch.setattr("backend.app.aspects.ownership.FirebaseRepository", factory)


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    _FakeWorkPlanService.calls = []
    app.dependency_overrides[_get_service] = lambda: _FakeWorkPlanService()
    # Desliga os demais aspectos para isolar a verificação de papel do Firestore.
    monkeypatch.setattr(aspect_config, "AUDIT_ENABLED", False)
    monkeypatch.setattr(aspect_config, "HISTORY_ENABLED", False)
    monkeypatch.setattr(aspect_config, "DEADLINE_VALIDATION_ENABLED", False)
    monkeypatch.setattr(aspect_config, "ALERTS_ENABLED", False)
    _patch_ownership_repo(monkeypatch)
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_aluno_autenticado_sem_header_e_autorizado(client: TestClient) -> None:
    # Cenário que a versão anterior rejeitava com 403 (actor.role="system").
    _override_user("aluno")

    response = client.post("/api/v1/tasks/task1/updates", json=_PROGRESS_UPDATE)

    assert response.status_code == 201
    assert _FakeWorkPlanService.calls == ["task1"]


def test_header_nao_sobrepoe_papel_do_jwt(client: TestClient) -> None:
    # JWT de aluno prevalece mesmo com header divergente.
    _override_user("aluno")

    response = client.post(
        "/api/v1/tasks/task1/updates",
        json=_PROGRESS_UPDATE,
        headers={"x-user-role": "coordenacao", "x-user-id": "spoof"},
    )

    assert response.status_code == 201
    assert _FakeWorkPlanService.calls == ["task1"]


def test_header_nao_escala_papel_nao_autorizado(client: TestClient) -> None:
    # Orientador autenticado não acessa, mesmo forjando x-user-role=aluno no header.
    _override_user("orientador")

    response = client.post(
        "/api/v1/tasks/task1/updates",
        json=_PROGRESS_UPDATE,
        headers={"x-user-role": "aluno", "x-user-id": "uid-aluno"},
    )

    assert response.status_code == 403
    assert _FakeWorkPlanService.calls == []
