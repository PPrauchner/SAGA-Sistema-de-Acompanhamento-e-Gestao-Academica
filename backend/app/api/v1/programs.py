"""
Router para os endpoints de configuração do programa acadêmico.

Responsabilidades:
- GET /programs: Listar programas cadastrados (id e nome) para seleção em formulários.
- GET /config: Recuperar a configuração atual do programa.
- PUT /config: Atualizar a configuração do programa (somente coordenação).
- Aplicar aspectos AOP: @requires_role, @audit_operation, @track_history.
"""

from fastapi import APIRouter, Depends, HTTPException
from backend.app.core.auth import get_current_user, CurrentUser
from backend.app.models.program_config import ProgramConfigUpdate
from backend.app.services.program_service import ProgramService


from backend.app.aspects.authorization import requires_role
from backend.app.aspects.audit import audit_operation
from backend.app.aspects.history import track_history

router = APIRouter(prefix="/programs", tags=["programs"])


@router.get("")
@requires_role("coordenacao", "orientador", "aluno")
async def list_programs(
    user: CurrentUser = Depends(get_current_user),
    service: ProgramService = Depends(ProgramService),
):
    """Lista os programas cadastrados para seleção nos formulários."""
    return await service.list_programs()


@router.get("/config")
@requires_role("coordenacao", "orientador", "aluno")
async def get_config(
    user: CurrentUser = Depends(get_current_user),
    service: ProgramService = Depends(ProgramService)
):
    """Busca a configuração do programa do usuário."""
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
    """Atualiza a configuração do programa."""
    success = await service.update_config(user.programa_id, data)
    if not success:
        raise HTTPException(status_code=500, detail="Falha ao atualizar configuração")
    return {"message": "Configuração atualizada com sucesso"}
