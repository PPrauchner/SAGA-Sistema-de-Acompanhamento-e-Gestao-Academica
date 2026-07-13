from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.app.api.v1 import dashboard
from backend.app.aspects import aspect_config
from backend.app.core.auth import CurrentUser, get_current_user
from backend.app.models.dashboard import (
    AlunoDashboardResponse,
    DashboardIndiceOrientadorResponse,
    IndiceModalidade,
    IndiceOrientadorResponse,
    PosicaoRelativaResponse,
)


class _FakeDashboardService:
    user: CurrentUser | None = None
    indice_call: tuple[str, IndiceModalidade] | None = None

    async def get_meu_aluno_dashboard(self, user: CurrentUser) -> AlunoDashboardResponse:
        type(self).user = user
        return AlunoDashboardResponse(
            student_id="student_real",
            nome="Aluno Real",
            situacao_registrada="regular",
            situacao_inferida="regular",
            conflito_situacao=False,
        )

    async def get_dashboard_indice_orientador(
        self,
        advisor_id: str,
        modalidade: IndiceModalidade,
    ) -> DashboardIndiceOrientadorResponse:
        type(self).indice_call = (advisor_id, modalidade)
        return DashboardIndiceOrientadorResponse(
            indice=IndiceOrientadorResponse(
                advisor_id=advisor_id,
                modalidade=modalidade,
                indice=12.5,
                total_orientandos=2,
                total_pontuacao=25.0,
            ),
            posicao_relativa=PosicaoRelativaResponse(
                modalidade=modalidade,
                media_programa=10.0,
                percentil=100.0,
                total_orientadores=1,
            ),
        )


def _client(user: CurrentUser) -> TestClient:
    app = FastAPI()
    app.include_router(dashboard.router, prefix="/api/v1")
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[dashboard.get_dashboard_service] = _FakeDashboardService
    _FakeDashboardService.user = None
    _FakeDashboardService.indice_call = None
    return TestClient(app)


def test_dashboard_aluno_me_usa_usuario_autenticado_sem_student_id() -> None:
    user = CurrentUser(uid="uid_aluno", role="aluno", programa_id="prog_default")
    response = _client(user).get("/api/v1/dashboard/aluno/me")

    assert response.status_code == 200
    assert response.json()["student_id"] == "student_real"
    assert _FakeDashboardService.user == user


def test_dashboard_aluno_me_bloqueia_papel_nao_aluno() -> None:
    user = CurrentUser(uid="uid_coord", role="coordenacao", programa_id="prog_default")
    response = _client(user).get("/api/v1/dashboard/aluno/me")

    assert response.status_code == 403
    assert _FakeDashboardService.user is None


def test_dashboard_indice_orientador_usa_modalidade_e_service(monkeypatch) -> None:
    monkeypatch.setattr(aspect_config, "AUTHORIZATION_ENABLED", False)
    user = CurrentUser(uid="uid_orientador", role="orientador", programa_id="prog_default")

    response = _client(user).get(
        "/api/v1/dashboard/orientador/adv_001/indice?modalidade=soma_total"
    )

    assert response.status_code == 200
    assert response.json()["indice"]["advisor_id"] == "adv_001"
    assert response.json()["indice"]["modalidade"] == "soma_total"
    assert _FakeDashboardService.indice_call == ("adv_001", IndiceModalidade.soma_total)
