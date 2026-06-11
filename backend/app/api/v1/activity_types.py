"""
Router for creditable activity types.

Responsabilidades:
- GET /activity-types: List activity types for the current program.
- POST /activity-types: Create a new activity type.
- PUT /activity-types/{type_id}: Update an existing activity type.
- PATCH /activity-types/{type_id}/toggle: Toggle the active status of an activity type.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from backend.app.core.auth import get_current_user, CurrentUser
from backend.app.models.activity_type import ActivityTypeCreate, ActivityTypeUpdate
from backend.app.services.activity_type_service import ActivityTypeService
from backend.app.aspects.authorization import requires_role
from backend.app.aspects.audit import audit_operation
from backend.app.aspects.history import track_history

router = APIRouter(prefix="/activity-types", tags=["activity-types"])


@router.get("")
@requires_role("coordenacao", "orientador", "aluno")
async def get_activity_types(
    user: CurrentUser = Depends(get_current_user),
    service: ActivityTypeService = Depends(ActivityTypeService)
):
    """Lists activity types for the program."""
    return service.get_all_by_program(user.programa_id)


@router.post("", status_code=status.HTTP_201_CREATED)
@requires_role("coordenacao")
@audit_operation
async def create_activity_type(
    data: ActivityTypeCreate,
    user: CurrentUser = Depends(get_current_user),
    service: ActivityTypeService = Depends(ActivityTypeService)
):
    """Creates a new activity type."""
    type_id = service.create_type(data)
    return {"id": type_id, "message": "Tipo de atividade criado com sucesso"}


@router.put("/{type_id}")
@requires_role("coordenacao")
@audit_operation
@track_history
async def update_activity_type(
    type_id: str,
    data: ActivityTypeUpdate,
    user: CurrentUser = Depends(get_current_user),
    service: ActivityTypeService = Depends(ActivityTypeService)
):
    """Updates an existing activity type."""
    success = service.update_type(type_id, data)
    if not success:
        raise HTTPException(status_code=404, detail="Tipo de atividade não encontrado")
    return {"message": "Tipo de atividade atualizado com sucesso"}


@router.patch("/{type_id}/toggle")
@requires_role("coordenacao")
@audit_operation
@track_history
async def toggle_activity_type(
    type_id: str,
    user: CurrentUser = Depends(get_current_user),
    service: ActivityTypeService = Depends(ActivityTypeService)
):
    """Toggles the active status of an activity type."""
    success = service.toggle_active(type_id)
    if not success:
        raise HTTPException(status_code=404, detail="Tipo de atividade não encontrado")
    return {"message": "Status do tipo de atividade alterado com sucesso"}
