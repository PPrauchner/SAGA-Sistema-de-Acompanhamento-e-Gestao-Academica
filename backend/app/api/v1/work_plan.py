"""Router FastAPI para plano de trabalho, etapas, tasks e progresso."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException, status

from backend.app.aspects.alerts import trigger_alerts
from backend.app.aspects.audit import audit_operation
from backend.app.aspects.authorization import requires_role
from backend.app.aspects.deadline_validation import check_deadlines
from backend.app.core.auth import CurrentUser, get_current_user
from backend.app.models.work_plan import (
    ActorContext,
    CreatePlanResponse,
    CreateStageResponse,
    CreateTaskResponse,
    MutationMessage,
    ProgressUpdateCreate,
    ProgressUpdateCreated,
    ProgressUpdateList,
    StageCreate,
    StageUpdate,
    TaskCreate,
    TaskStatusPatch,
    TaskStatusResponse,
    TaskUpdate,
    WorkPlanCreate,
    WorkPlanFact,
    WorkPlanFull,
    WorkPlanUpdate,
)
from backend.app.repositories.work_plan_repository import WorkPlanRepository
from backend.app.services.work_plan_service import WorkPlanNotFoundError, WorkPlanService, _build_progress_update_alert

router = APIRouter()


def _get_service() -> WorkPlanService:
    return WorkPlanService(WorkPlanRepository())


def _actor(
    x_user_id: str | None = Header(default=None),
    x_user_name: str | None = Header(default=None),
    x_user_role: str | None = Header(default=None),
) -> ActorContext:
    role = x_user_role if x_user_role in {"aluno", "orientador", "coordenacao"} else "system"
    return ActorContext(uid=x_user_id or "system", nome=x_user_name or "Sistema", role=role)


def _not_found(exc: WorkPlanNotFoundError) -> HTTPException:
    return HTTPException(status_code=404, detail=f"Plano de trabalho não encontrado: {exc}")


@router.get("/work-plan/{student_id}", response_model=WorkPlanFull)
async def get_work_plan(
    student_id: str,
    service: WorkPlanService = Depends(_get_service),
) -> WorkPlanFull:
    try:
        return await service.get_plan(student_id)
    except WorkPlanNotFoundError as exc:
        raise _not_found(exc)


@router.post("/work-plan/{student_id}", response_model=CreatePlanResponse, status_code=status.HTTP_201_CREATED)
@requires_role("orientador", "coordenacao")
@audit_operation
async def create_work_plan(
    student_id: str,
    payload: WorkPlanCreate,
    user: CurrentUser = Depends(get_current_user),
    service: WorkPlanService = Depends(_get_service),
) -> CreatePlanResponse:
    return await service.create_plan(student_id, payload)


@router.put("/work-plan/{plan_id}", response_model=dict)
@requires_role("orientador", "coordenacao")
@audit_operation
async def update_work_plan(
    plan_id: str,
    payload: WorkPlanUpdate,
    user: CurrentUser = Depends(get_current_user),
    service: WorkPlanService = Depends(_get_service),
) -> dict:
    try:
        return await service.update_plan(plan_id, payload)
    except WorkPlanNotFoundError as exc:
        raise _not_found(exc)


@router.post("/work-plan/{plan_id}/stages", response_model=CreateStageResponse, status_code=status.HTTP_201_CREATED)
@requires_role("orientador", "coordenacao")
@audit_operation
async def create_stage(
    plan_id: str,
    payload: StageCreate,
    user: CurrentUser = Depends(get_current_user),
    service: WorkPlanService = Depends(_get_service),
) -> CreateStageResponse:
    try:
        return await service.create_stage(plan_id, payload)
    except WorkPlanNotFoundError as exc:
        raise _not_found(exc)


@router.patch("/stages/{stage_id}", response_model=MutationMessage)
@requires_role("orientador", "coordenacao")
@audit_operation
async def update_stage(
    stage_id: str,
    payload: StageUpdate,
    user: CurrentUser = Depends(get_current_user),
    service: WorkPlanService = Depends(_get_service),
) -> MutationMessage:
    try:
        result = await service.update_stage(stage_id, payload)
        return MutationMessage(**result)
    except WorkPlanNotFoundError as exc:
        raise _not_found(exc)


@router.post("/stages/{stage_id}/tasks", response_model=CreateTaskResponse, status_code=status.HTTP_201_CREATED)
@requires_role("orientador", "coordenacao")
@audit_operation
async def create_task(
    stage_id: str,
    payload: TaskCreate,
    user: CurrentUser = Depends(get_current_user),
    service: WorkPlanService = Depends(_get_service),
) -> CreateTaskResponse:
    try:
        return await service.create_task(stage_id, payload)
    except WorkPlanNotFoundError as exc:
        raise _not_found(exc)


@router.patch("/tasks/{task_id}", response_model=MutationMessage)
@requires_role("orientador", "coordenacao")
@audit_operation
async def update_task(
    task_id: str,
    payload: TaskUpdate,
    user: CurrentUser = Depends(get_current_user),
    service: WorkPlanService = Depends(_get_service),
) -> MutationMessage:
    try:
        result = await service.update_task(task_id, payload)
        return MutationMessage(**result)
    except WorkPlanNotFoundError as exc:
        raise _not_found(exc)


@router.patch("/tasks/{task_id}/status", response_model=TaskStatusResponse)
@requires_role("orientador", "coordenacao")
@audit_operation
async def update_task_status(
    task_id: str,
    payload: TaskStatusPatch,
    user: CurrentUser = Depends(get_current_user),
    service: WorkPlanService = Depends(_get_service),
) -> TaskStatusResponse:
    try:
        return await service.update_task_status(task_id, payload.status)
    except WorkPlanNotFoundError as exc:
        raise _not_found(exc)


@router.post("/tasks/{task_id}/updates", response_model=ProgressUpdateCreated, status_code=status.HTTP_201_CREATED)
@requires_role("aluno")
@audit_operation
@check_deadlines
@trigger_alerts(_build_progress_update_alert)
async def add_progress_update(
    task_id: str,
    payload: ProgressUpdateCreate,
    actor: ActorContext = Depends(_actor),
    user: CurrentUser = Depends(get_current_user),
    service: WorkPlanService = Depends(_get_service),
) -> ProgressUpdateCreated:
    try:
        return await service.add_progress_update(task_id, payload, actor)
    except WorkPlanNotFoundError as exc:
        raise _not_found(exc)


@router.get("/tasks/{task_id}/updates", response_model=ProgressUpdateList)
async def list_progress_updates(
    task_id: str,
    service: WorkPlanService = Depends(_get_service),
) -> ProgressUpdateList:
    try:
        return await service.list_updates(task_id)
    except WorkPlanNotFoundError as exc:
        raise _not_found(exc)


@router.get("/work-plan/{student_id}/facts/plano-concluido", response_model=WorkPlanFact)
async def get_plan_concluded_fact(
    student_id: str,
    service: WorkPlanService = Depends(_get_service),
) -> WorkPlanFact:
    try:
        return await service.get_plan_fact(student_id)
    except WorkPlanNotFoundError as exc:
        raise _not_found(exc)
