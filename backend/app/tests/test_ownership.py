import os
os.environ.setdefault("FIREBASE_PROJECT_ID", "test-project")
os.environ.setdefault("FIREBASE_PRIVATE_KEY", "test-key")
os.environ.setdefault("FIREBASE_CLIENT_EMAIL", "test@test.iam.gserviceaccount.com")

import pytest
from fastapi import FastAPI, HTTPException
from unittest.mock import AsyncMock, patch

from backend.app.aspects.ownership import check_dashboard_ownership
from backend.app.core.auth import CurrentUser

app = FastAPI()

@app.get("/api/v1/dashboard/aluno/{student_id}")
@check_dashboard_ownership()
async def aluno_dashboard(student_id: str, current_user: CurrentUser):
    return {"message": "ok"}

@app.get("/api/v1/dashboard/orientador/{advisor_id}")
@check_dashboard_ownership()
async def orientador_dashboard(advisor_id: str, current_user: CurrentUser):
    return {"message": "ok"}

@pytest.fixture
def override_config():
    with patch("backend.app.aspects.aspect_config.AUTHORIZATION_ENABLED", True):
        yield

@pytest.mark.asyncio
async def test_ownership_aluno_access_other_student(override_config):
    user = CurrentUser(uid="uid_aluno_meu", email="aluno@test", role="aluno", programa_id="p1")
    student_doc = {"id": "stu_outro", "uid": "uid_aluno_outro"}

    with patch("backend.app.aspects.ownership.FirebaseRepository") as MockFBR:
        mock_repo_instance = AsyncMock()
        mock_repo_instance.get.return_value = student_doc
        MockFBR.return_value = mock_repo_instance

        with pytest.raises(HTTPException) as exc:
            await aluno_dashboard(student_id="stu_outro", current_user=user)
        assert exc.value.status_code == 403
        assert "aluno só pode acessar próprio dashboard" in exc.value.detail

@pytest.mark.asyncio
async def test_ownership_orientador_access_not_orientando(override_config):
    user = CurrentUser(uid="uid_orientador_1", email="ori@test", role="orientador", programa_id="p1")
    student_doc = {"id": "stu_qualquer", "uid": "uid_aluno", "orientador_id": "adv_2"}
    advisor_doc = {"id": "adv_1", "uid": "uid_orientador_1"}

    with patch("backend.app.aspects.ownership.FirebaseRepository") as MockFBR:
        mock_repo_instance = AsyncMock()
        mock_repo_instance.query.return_value = [advisor_doc]
        mock_repo_instance.get.return_value = student_doc
        MockFBR.return_value = mock_repo_instance

        with pytest.raises(HTTPException) as exc:
            await aluno_dashboard(student_id="stu_qualquer", current_user=user)
        assert exc.value.status_code == 403
        assert "o aluno não é seu orientando" in exc.value.detail

@pytest.mark.asyncio
async def test_ownership_orientador_access_other_advisor(override_config):
    user = CurrentUser(uid="uid_orientador_1", email="ori@test", role="orientador", programa_id="p1")
    advisor_doc = {"id": "adv_2", "uid": "uid_orientador_2"}

    with patch("backend.app.aspects.ownership.FirebaseRepository") as MockFBR:
        mock_repo_instance = AsyncMock()
        mock_repo_instance.get.return_value = advisor_doc
        MockFBR.return_value = mock_repo_instance

        with pytest.raises(HTTPException) as exc:
            await orientador_dashboard(advisor_id="adv_2", current_user=user)
        assert exc.value.status_code == 403
        assert "orientador só pode acessar próprio dashboard" in exc.value.detail
