"""
Roteador para tipos de atividades creditáveis.

Responsabilidades:
- GET /activity-types: Lista os tipos de atividades para o programa atual.
- POST /activity-types: Cria um novo tipo de atividade.
- PUT /activity-types/{type_id}: Atualiza um tipo de atividade existente.
- PATCH /activity-types/{type_id}/toggle: Ativa ou desativa o status de um tipo de atividade.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from backend.app.core.auth import get_current_user, CurrentUser
from backend.app.models.activity_type import ActivityTypeCreate, ActivityTypeUpdate, ActivityTypeResponse, ActivityTypeToggleRequest
from backend.app.services.activity_type_service import ActivityTypeService
from backend.app.aspects.authorization import requires_role
from backend.app.aspects.audit import audit_operation
from backend.app.aspects.history import track_history

router = APIRouter(prefix="/activity-types", tags=["activity-types"])


@router.get("", response_model=list[ActivityTypeResponse])
@requires_role("coordenacao", "orientador", "aluno")
async def get_activity_types(
    user: CurrentUser = Depends(get_current_user),
    service: ActivityTypeService = Depends(ActivityTypeService)
):
    """Lista os tipos de atividades para o programa atual."""
    return await service.get_all_by_program(user.programa_id)


@router.post("", status_code=status.HTTP_201_CREATED)
@requires_role("coordenacao")
@audit_operation
async def create_activity_type(
    data: ActivityTypeCreate,
    user: CurrentUser = Depends(get_current_user),
    service: ActivityTypeService = Depends(ActivityTypeService)
) -> dict:
    """Cria um novo tipo de atividade."""
    result = await service.create_type(data, user)
    if isinstance(result, dict):
        result["message"] = "Tipo de atividade criado com sucesso"
        return result
    return {"id": result, "message": "Tipo de atividade criado com sucesso"}


@router.put("/{type_id}")
@requires_role("coordenacao")
@audit_operation
@track_history
async def update_activity_type(
    type_id: str,
    data: ActivityTypeUpdate,
    user: CurrentUser = Depends(get_current_user),
    service: ActivityTypeService = Depends(ActivityTypeService)
) -> dict:
    """Atualiza um tipo de atividade existente."""
    result = await service.update_type(type_id, data, user)
    if isinstance(result, dict):
        return result
    return {"message": "Tipo de atividade atualizado com sucesso"}


@router.patch("/{type_id}/toggle")
@requires_role("coordenacao")
@audit_operation
@track_history
async def toggle_activity_type(
    type_id: str,
    data: ActivityTypeToggleRequest,
    user: CurrentUser = Depends(get_current_user),
    service: ActivityTypeService = Depends(ActivityTypeService)
) -> dict:
    """Ativa ou desativa o status de um tipo de atividade."""
    result = await service.toggle_active(type_id, data, user)
    if isinstance(result, dict):
        return result
    return {"message": "Status do tipo de atividade alterado com sucesso"}
