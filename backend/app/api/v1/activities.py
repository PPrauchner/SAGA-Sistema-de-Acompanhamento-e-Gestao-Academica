"""
Router FastAPI para atividades creditáveis.

Responsabilidades:
- GET  /api/v1/activities                          : lista atividades por papel.
- POST /api/v1/activities                          : aluno registra atividade + RL04.
- PATCH /api/v1/activities/{id}/validate           : orientador/coordenação valida.
- POST /api/v1/activities/{id}/comprovante         : upload de comprovante para Firebase Storage.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status

from backend.app.aspects.alerts import trigger_alerts
from backend.app.aspects.audit import audit_operation
from backend.app.aspects.authorization import requires_role
from backend.app.aspects.deadline_validation import check_deadlines
from backend.app.core.auth import CurrentUser, get_current_user
from backend.app.models.activity import (
    ActivityCreate,
    ActivityResponse,
    ActivitySubmitResponse,
    ActivityValidateRequest,
    ActivityValidateResponse,
)
from backend.app.services.activity_service import ActivityService

router = APIRouter(tags=["activities"])
_service = ActivityService()


@router.get("/activities", response_model=list[ActivityResponse])
async def list_activities(
    student_id: str | None = None,
    status: str | None = None,
    categoria: str | None = None,
    current_user: CurrentUser = Depends(get_current_user),
) -> list[dict]:
    return await _service.list_activities(
        current_user=current_user,
        student_id=student_id,
        status_filter=status,
        categoria_filter=categoria,
    )


@router.post("/activities", response_model=ActivitySubmitResponse, status_code=201)
@requires_role("aluno")
@audit_operation
@check_deadlines
@trigger_alerts
async def create_activity(
    body: ActivityCreate,
    current_user: CurrentUser = Depends(get_current_user),
) -> dict:
    return await _service.submit_activity(body=body, current_user=current_user)


@router.patch(
    "/activities/{activity_id}/validate",
    response_model=ActivityValidateResponse,
)
@audit_operation
@trigger_alerts
async def validate_activity(
    activity_id: str,
    body: ActivityValidateRequest,
    student_id: str,
    current_user: CurrentUser = Depends(get_current_user),
) -> dict:
    if body.acao == "parecer_orientador":
        # Orientador emite parecer
        return await _service.advisor_review(
            student_id=student_id,
            activity_id=activity_id,
            observacao=body.observacao or "",
            current_user=current_user,
        )
    # Coordenação aprova/rejeita
    return await _service.validate_activity(
        student_id=student_id,
        activity_id=activity_id,
        body=body,
        current_user=current_user,
    )


@router.post("/activities/{activity_id}/comprovante")
async def upload_comprovante(
    activity_id: str,
    student_id: str,
    file: UploadFile,
    current_user: CurrentUser = Depends(get_current_user),
) -> dict[str, str]:
    """Faz upload do comprovante para Firebase Storage e grava comprovante_url.

    Args:
        activity_id: ID da atividade.
        student_id: UID do aluno dono da atividade.
        file: Arquivo PDF ou imagem enviado.
        current_user: Usuário autenticado (aluno ou coordenação).

    Returns:
        Dict com comprovante_url gravado na atividade.
    """
    if current_user.role == "aluno" and current_user.uid != student_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado",
        )

    allowed_types = {
        "application/pdf",
        "image/jpeg",
        "image/png",
        "image/webp",
    }
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Tipo de arquivo não permitido: {file.content_type}",
        )

    contents = await file.read()

    try:
        from firebase_admin import storage as fb_storage
        from backend.app.core.firebase import init_firebase

        init_firebase()
        bucket = fb_storage.bucket()
        ext = file.filename.rsplit(".", 1)[-1] if file.filename and "." in file.filename else "bin"
        blob_path = f"comprovantes/{student_id}/{activity_id}.{ext}"
        blob = bucket.blob(blob_path)
        blob.upload_from_string(contents, content_type=file.content_type)
        blob.make_public()
        url: str = blob.public_url
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro no upload: {exc}",
        ) from exc

    from backend.app.repositories.activity_repository import ActivityRepository
    repo = ActivityRepository()
    await repo.save_comprovante_url(student_id, activity_id, url)

    return {"comprovante_url": url}
