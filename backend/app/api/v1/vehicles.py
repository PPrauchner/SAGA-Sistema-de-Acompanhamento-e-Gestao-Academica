"""
Router para veículos de publicação e seus níveis de relevância específicos por programa.

Responsabilidades:
- GET /vehicles: Listar veículos com seus níveis de relevância e pesos para o programa.
- POST /vehicles: Registrar um novo veículo e seu nível de relevância inicial.
- GET /vehicle-levels: Listar os níveis de relevância configurados para os veículos no programa.
- PUT /vehicle-levels/{vehicle_id}: Atualizar o nível de relevância/peso de um veículo no programa.
"""

from fastapi import APIRouter, Depends, HTTPException
from backend.app.core.auth import get_current_user, CurrentUser
from backend.app.models.vehicle_level import VehicleLevelUpdate, VehicleLevelCreate
from backend.app.services.program_service import ProgramService
from backend.app.aspects.authorization import requires_role
from backend.app.aspects.audit import audit_operation

router = APIRouter(tags=["vehicles"])


@router.get("/vehicle-levels")
@requires_role("coordenacao", "orientador")
async def get_vehicle_levels(
    user: CurrentUser = Depends(get_current_user),
    service: ProgramService = Depends(ProgramService)
):
    """Lista os níveis de relevância e pesos de veículos configurados no programa atual."""
    return await service.get_vehicle_levels(user.programa_id)


@router.put("/vehicle-levels/{vehicle_id}")
@requires_role("coordenacao")
@audit_operation
async def update_vehicle_level(
    vehicle_id: str,
    data: VehicleLevelUpdate,
    user: CurrentUser = Depends(get_current_user),
    service: ProgramService = Depends(ProgramService)
):
    """Atualiza o nível de relevância e o peso de um veículo no programa atual."""
    # Passamos o vehicle_id do path e o restante do body
    success = await service.update_vehicle_level(user.programa_id, vehicle_id, data)
    if not success:
        raise HTTPException(status_code=500, detail="Falha ao atualizar nível do veículo")
    return {"message": "Nível do veículo atualizado com sucesso"}
