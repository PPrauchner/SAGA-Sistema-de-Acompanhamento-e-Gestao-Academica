"""
Router FastAPI para os endpoints de veículos de publicação (eventos e revistas).

Responsabilidades:
- GET /api/v1/vehicles: lista veículos com nível de relevância e peso do programa atual,
  carregados de programs/prog_default/vehicle_levels/. Acessível por todos os papéis.
- POST /api/v1/vehicles: coordenação cadastra novo veículo e define nível de relevância
  inicial. Aplica @requires_role('coordenacao') e @audit_operation.
- PUT /api/v1/vehicle-levels/{vehicle_id}: coordenação atualiza nível de relevância de
  um veículo no programa. Altera fatos nivel_relevancia e relevancia_peso usados pelo
  motor RL05. Aplica @requires_role('coordenacao') e @audit_operation.
- DELETE /api/v1/vehicles/{vehicle_id}: coordenação remove um veículo e seu nível de
  relevância no programa. Aplica @requires_role('coordenacao') e @audit_operation.
"""

from fastapi import APIRouter, Depends, status

from backend.app.aspects.audit import audit_operation
from backend.app.aspects.authorization import requires_role
from backend.app.core.auth import CurrentUser, get_current_user
from backend.app.models.vehicle import VehicleCreate, VehicleLevelUpdate
from backend.app.services.vehicle_service import VehicleService

router = APIRouter()


@router.get("/vehicles")
@requires_role("coordenacao", "orientador", "aluno")
async def list_vehicles(
    user: CurrentUser = Depends(get_current_user),
    service: VehicleService = Depends(VehicleService),
) -> list[dict]:
    return await service.list_vehicles(user)


@router.post(
    "/vehicles",
    status_code=status.HTTP_201_CREATED,
)
@requires_role("coordenacao")
@audit_operation
async def create_vehicle(
    body: VehicleCreate,
    user: CurrentUser = Depends(get_current_user),
    service: VehicleService = Depends(VehicleService),
) -> dict:
    return await service.create_vehicle(body, user)


@router.put("/vehicle-levels/{vehicle_id}")
@requires_role("coordenacao")
@audit_operation
async def update_vehicle_level(
    vehicle_id: str,
    body: VehicleLevelUpdate,
    user: CurrentUser = Depends(get_current_user),
    service: VehicleService = Depends(VehicleService),
) -> dict:
    return await service.update_vehicle_level(vehicle_id, body, user)


@router.delete("/vehicles/{vehicle_id}")
@requires_role("coordenacao")
@audit_operation
async def delete_vehicle(
    vehicle_id: str,
    user: CurrentUser = Depends(get_current_user),
    service: VehicleService = Depends(VehicleService),
) -> dict:
    return await service.delete_vehicle(vehicle_id, user)
