"""
Router FastAPI para tipos de atividade creditável.

Responsabilidades:
- GET  /api/v1/activity-types         : lista tipos (todos os papéis autenticados).
- POST /api/v1/activity-types         : cria tipo (coordenacao).
- PUT  /api/v1/activity-types/{id}    : atualiza tipo com histórico A03 (coordenacao).
- PATCH /api/v1/activity-types/{id}/toggle : ativa/desativa com histórico A03 (coordenacao).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from backend.app.core.auth import CurrentUser, get_current_user
from backend.app.models.activity import (
    ActivityTypeCreate,
    ActivityTypeResponse,
    ActivityTypeUpdate,
)
from backend.app.services.activity_type_service import ActivityTypeService

router = APIRouter(tags=["activity-types"])
_service = ActivityTypeService()


@router.get("/activity-types", response_model=list[ActivityTypeResponse])
async def list_activity_types(
    only_active: bool = False,
    current_user: CurrentUser = Depends(get_current_user),
) -> list[dict]:
    return await _service.list_types(only_active=only_active)


@router.post("/activity-types", response_model=ActivityTypeResponse, status_code=201)
async def create_activity_type(
    body: ActivityTypeCreate,
    current_user: CurrentUser = Depends(get_current_user),
) -> dict:
    return await _service.create_type(body=body, current_user=current_user)


@router.put("/activity-types/{type_id}", response_model=ActivityTypeResponse)
async def update_activity_type(
    type_id: str,
    body: ActivityTypeUpdate,
    current_user: CurrentUser = Depends(get_current_user),
) -> dict:
    return await _service.update_type(
        type_id=type_id, body=body, current_user=current_user
    )


@router.patch("/activity-types/{type_id}/toggle", response_model=ActivityTypeResponse)
async def toggle_activity_type(
    type_id: str,
    current_user: CurrentUser = Depends(get_current_user),
) -> dict:
    return await _service.toggle_active(type_id=type_id, current_user=current_user)
