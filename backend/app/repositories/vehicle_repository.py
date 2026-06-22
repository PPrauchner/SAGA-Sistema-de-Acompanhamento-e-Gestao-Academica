"""
Repositório concreto para a coleção vehicles/ e a subcoleção de níveis de relevância.

Responsabilidades:
- Herdar FirebaseRepository e especializar operações para a coleção vehicles/ (CRUD básico
  via create/get/list_all/delete herdados).
- list_levels(programa_id): lê programs/{programa_id}/vehicle_levels/ (nível e peso por
  veículo) — fatos usados pelo motor RL05.
- set_level(programa_id, veiculo_id, data): grava/sobrescreve o nível de relevância de um
  veículo no programa, usando veiculo_id como id do documento.
- delete_level(programa_id, veiculo_id): remove o nível de relevância do veículo no programa.

Restrição: sem lógica de negócio — apenas leitura e escrita. O peso por nível é resolvido
pelo VehicleService.
"""

from __future__ import annotations

from typing import Any

from backend.app.repositories.firebase_repository import FirebaseRepository

_VEHICLE_LEVELS_SUBCOLLECTION = "vehicle_levels"


class VehicleRepository(FirebaseRepository):
    """Repositório específico da coleção vehicles e dos níveis de relevância do programa."""

    def __init__(self) -> None:
        super().__init__("vehicles")
        self._programs = FirebaseRepository("programs")

    async def list_levels(self, programa_id: str) -> list[dict[str, Any]]:
        return await self._programs.list_subcollection(
            programa_id, _VEHICLE_LEVELS_SUBCOLLECTION
        )

    async def set_level(
        self,
        programa_id: str,
        veiculo_id: str,
        data: dict[str, Any],
    ) -> None:
        await self._programs.set_subcollection(
            programa_id, _VEHICLE_LEVELS_SUBCOLLECTION, veiculo_id, data
        )

    async def delete_level(self, programa_id: str, veiculo_id: str) -> None:
        await self._programs.delete_subcollection(
            programa_id, _VEHICLE_LEVELS_SUBCOLLECTION, veiculo_id
        )
