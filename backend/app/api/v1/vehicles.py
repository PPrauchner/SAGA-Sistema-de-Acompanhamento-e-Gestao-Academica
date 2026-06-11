"""
Router for publication vehicles and their program-specific relevance levels.

Responsabilidades:
- GET /vehicles: List vehicles with their relevance levels and weights for the program.
- POST /vehicles: Register a new vehicle and its initial relevance level.
- PUT /vehicle-levels/{vehicle_id}: Update the relevance level/weight of a vehicle in the program.
"""

from fastapi import APIRouter, Depends, HTTPException
from backend.app.core.auth import get_current_user, CurrentUser
from backend.app.models.vehicle_level import VehicleLevelUpdate, VehicleLevelCreate
from backend.app.services.program_service import ProgramService
from backend.app.aspects.authorization import requires_role
from backend.app.aspects.audit import audit_operation

router = APIRouter(tags=["vehicles"])


@router.put("/vehicle-levels/{vehicle_id}")
@requires_role("coordenacao")
@audit_operation
async def update_vehicle_level(
    vehicle_id: str,
    data: VehicleLevelUpdate,
    user: CurrentUser = Depends(get_current_user),
    service: ProgramService = Depends(ProgramService)
):
    """Updates the relevance level and weight of a vehicle in the current program."""
    # We pass the vehicle_id from the path and the rest from the body
    # Ensuring veiculo_id matches if provided in body or just using path one
    success = service.update_vehicle_level(user.programa_id, vehicle_id, data)
    if not success:
        raise HTTPException(status_code=500, detail="Falha ao atualizar nível do veículo")
    return {"message": "Nível do veículo atualizado com sucesso"}
