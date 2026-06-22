"""
Serviço de negócio para veículos de publicação e seus níveis de relevância.

Responsabilidades:
- list_vehicles(): lista veículos do programa juntando o nível de relevância e o peso
  configurados em programs/{id}/vehicle_levels/ — base dos fatos RL05.
- create_vehicle(): coordenação cadastra um veículo e define seu nível inicial; o peso é
  derivado do nível pela tabela PESO_POR_NIVEL.
- update_vehicle_level(): coordenação altera o nível de relevância de um veículo, recalculando
  o peso. Altera os fatos nivel_relevancia e relevancia_peso usados pelo motor RL05.
- delete_vehicle(): coordenação remove um veículo e seu nível de relevância no programa.

Restrição: única camada que conhece a regra nível→peso; o repositório apenas persiste.
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import HTTPException, status

from backend.app.core.auth import CurrentUser
from backend.app.models.vehicle import VehicleCreate, VehicleLevelUpdate
from backend.app.repositories.vehicle_repository import VehicleRepository

PESO_POR_NIVEL: dict[str, float] = {
    "A1": 1.0,
    "A2": 0.85,
    "A3": 0.7,
    "A4": 0.7,
    "B1": 0.5,
    "B2": 0.5,
    "SC": 0.2,
}


class VehicleService:
    """Serviço de negócio para veículos e níveis de relevância."""

    def __init__(self) -> None:
        self._vehicles = VehicleRepository()

    async def list_vehicles(self, user: CurrentUser) -> list[dict]:
        vehicles = await self._vehicles.list_all()
        levels = await self._vehicles.list_levels(user.programa_id)
        level_by_vehicle = {level["id"]: level for level in levels}

        result: list[dict] = []
        for vehicle in vehicles:
            if vehicle.get("programa_id") != user.programa_id:
                continue
            level = level_by_vehicle.get(vehicle["id"], {})
            nivel = level.get("nivel", "SC")
            result.append(
                {
                    "id": vehicle["id"],
                    "nome": vehicle.get("nome"),
                    "tipo": vehicle.get("tipo"),
                    "sigla": vehicle.get("sigla"),
                    "issn": vehicle.get("issn"),
                    "nivel": nivel,
                    "peso": level.get("peso", PESO_POR_NIVEL.get(nivel, PESO_POR_NIVEL["SC"])),
                }
            )
        return result

    async def create_vehicle(self, data: VehicleCreate, user: CurrentUser) -> dict:
        peso = PESO_POR_NIVEL[data.nivel]
        vehicle_id = await self._vehicles.create(
            {
                "nome": data.nome,
                "tipo": data.tipo,
                "sigla": data.sigla,
                "issn": data.issn,
                "programa_id": user.programa_id,
                "criado_em": datetime.now(timezone.utc),
            }
        )
        await self._vehicles.set_level(
            user.programa_id,
            vehicle_id,
            {
                "veiculo_id": vehicle_id,
                "nivel": data.nivel,
                "peso": peso,
                "atualizado_em": datetime.now(timezone.utc),
                "atualizado_por": user.uid,
            },
        )

        return {"id": vehicle_id, "peso_atribuido": peso}

    async def update_vehicle_level(
        self,
        vehicle_id: str,
        data: VehicleLevelUpdate,
        user: CurrentUser,
    ) -> dict:
        vehicle = await self._vehicles.get(vehicle_id)
        if vehicle is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Veículo não encontrado",
            )

        peso = PESO_POR_NIVEL[data.nivel]
        await self._vehicles.set_level(
            user.programa_id,
            vehicle_id,
            {
                "veiculo_id": vehicle_id,
                "nivel": data.nivel,
                "peso": peso,
                "atualizado_em": datetime.now(timezone.utc),
                "atualizado_por": user.uid,
            },
        )

        return {"message": "Nível de relevância atualizado", "peso_atribuido": peso}

    async def delete_vehicle(self, vehicle_id: str, user: CurrentUser) -> dict:
        vehicle = await self._vehicles.get(vehicle_id)
        if vehicle is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Veículo não encontrado",
            )

        await self._vehicles.delete_level(user.programa_id, vehicle_id)
        await self._vehicles.delete(vehicle_id)

        return {"message": "Veículo removido"}
