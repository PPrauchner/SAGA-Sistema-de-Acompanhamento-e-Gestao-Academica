"""
Router for academic program configuration endpoints.

Responsabilidades:
- GET /config: Retrieve the current program configuration.
- PUT /config: Update program configuration (coordination only).
- Apply AOP aspects: @requires_role, @audit_operation, @track_history.
"""

from fastapi import APIRouter, Depends, HTTPException
from backend.app.core.auth import get_current_user, CurrentUser
from backend.app.models.program_config import ProgramConfigUpdate
from backend.app.services.program_service import ProgramService


from backend.app.aspects.authorization import requires_role
from backend.app.aspects.audit import audit_operation
from backend.app.aspects.history import track_history

router = APIRouter(prefix="/programs", tags=["programs"])


@router.get("/config")
@requires_role("coordenacao", "orientador", "aluno")
async def get_config(
    user: CurrentUser = Depends(get_current_user),
    service: ProgramService = Depends(ProgramService)
):
    """Fetches the configuration for the user's program."""
    config = await service.get_config(user.programa_id)
    if not config:
        raise HTTPException(status_code=404, detail="Configuração não encontrada")
    return config


@router.put("/config")
@requires_role("coordenacao")
@audit_operation
@track_history
async def update_config(
    data: ProgramConfigUpdate,
    user: CurrentUser = Depends(get_current_user),
    service: ProgramService = Depends(ProgramService)
):
    """Updates the program configuration."""
    success = await service.update_config(user.programa_id, data)
    if not success:
        raise HTTPException(status_code=500, detail="Falha ao atualizar configuração")
    return {"message": "Configuração atualizada com sucesso"}
