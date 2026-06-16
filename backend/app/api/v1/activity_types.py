"""
Router FastAPI para os endpoints de tipos de atividade creditável.

Responsabilidades:
- GET /api/v1/activity-types: lista tipos de atividade do programa. Acessível por todos
  os papéis autenticados.
- POST /api/v1/activity-types: cria novo tipo de atividade com pontuação, limite,
  categoria e flags. Aplica @requires_role('coordenacao') e @audit_operation.
- PUT /api/v1/activity-types/{type_id}: atualiza tipo de atividade — aciona aspecto de
  histórico (@track_history) pois alterações em pontuação ou limite afetam fatos do motor.
  Aplica @requires_role('coordenacao'), @audit_operation e @track_history.
- PATCH /api/v1/activity-types/{type_id}/toggle: ativa ou desativa o tipo.
  Aplica @requires_role('coordenacao'), @audit_operation e @track_history, pois mudança
  em ativo afeta o fato tipo_ativo do motor lógico.
"""

from fastapi import APIRouter, Depends, status

from backend.app.aspects.audit import audit_operation
from backend.app.aspects.authorization import requires_role
from backend.app.aspects.history import track_history
from backend.app.core.auth import CurrentUser, get_current_user
from backend.app.models.activity_type import (
    ActivityTypeCreateRequest,
    ActivityTypeToggleRequest,
    ActivityTypeUpdateRequest,
)
from backend.app.services.activity_type_service import ActivityTypeService

router = APIRouter()

service = ActivityTypeService()


@router.get("/activity-types")
@requires_role("coordenacao", "orientador", "aluno")
async def list_activity_types(
    user: CurrentUser = Depends(get_current_user),
) -> list[dict]:
    return await service.list_types()


@router.post(
    "/activity-types",
    status_code=status.HTTP_201_CREATED,
)
@requires_role("coordenacao")
@audit_operation
async def create_activity_type(
    body: ActivityTypeCreateRequest,
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    return await service.create_type(body, user)


@router.put("/activity-types/{type_id}")
@requires_role("coordenacao")
@audit_operation
@track_history
async def update_activity_type(
    type_id: str,
    body: ActivityTypeUpdateRequest,
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    return await service.update_type(type_id, body, user)


@router.patch("/activity-types/{type_id}/toggle")
@requires_role("coordenacao")
@audit_operation
@track_history
async def toggle_activity_type(
    type_id: str,
    body: ActivityTypeToggleRequest,
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    return await service.toggle_active(type_id, body, user)
