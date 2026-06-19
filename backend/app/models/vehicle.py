"""
Modelos Pydantic para a entidade Vehicle (veículo de publicação) e seu nível de relevância.

Responsabilidades:
- Definir VehicleCreate para POST /api/v1/vehicles (coordenação cadastra veículo e nível).
- Definir VehicleLevelUpdate para PUT /api/v1/vehicle-levels/{vehicle_id} (altera o nível
  de relevância do veículo no programa, base dos fatos RL05).
- Definir VehicleResponse para leitura, incluindo nivel e peso resolvidos de
  programs/prog_default/vehicle_levels/.
- Mapear o documento Firestore da coleção vehicles/; o nível fica em
  programs/{id}/vehicle_levels/{veiculo_id}.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

VehicleType = Literal["evento", "revista"]

RelevanceLevel = Literal["A1", "A2", "A3", "A4", "B1", "B2", "SC"]


class VehicleCreate(BaseModel):
    nome: str
    tipo: VehicleType
    sigla: str | None = None
    issn: str | None = None
    nivel: RelevanceLevel


class VehicleLevelUpdate(BaseModel):
    nivel: RelevanceLevel


class VehicleResponse(BaseModel):
    id: str
    nome: str
    tipo: VehicleType
    sigla: str | None = None
    issn: str | None = None
    nivel: RelevanceLevel
    peso: float
