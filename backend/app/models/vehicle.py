"""
Modelos Pydantic do Vehicle e escala de relevância Qualis (fonte de verdade dos pesos RL05).

Responsabilidades:
- Definir VehicleCreate para POST /api/v1/vehicles (coordenação cadastra veículo e nível).
- Definir VehicleLevelUpdate para PUT /api/v1/vehicle-levels/{vehicle_id} (altera o nível
  de relevância do veículo no programa, base dos fatos RL05).
- Definir VehicleResponse para leitura, incluindo nivel e peso resolvidos de
  programs/prog_default/vehicle_levels/.
- Mapear o documento Firestore da coleção vehicles/; o nível fica em
  programs/{id}/vehicle_levels/{veiculo_id}.
- Declarar RelevanceLevel: os 7 níveis canônicos do Qualis Único da CAPES.
- Declarar PESO_POR_NIVEL: a escala de pesos monotônica única consumida pela RL05,
  fonte de verdade para inference_repository, fixtures e seed_firestore.
- Declarar os campos descritivos do veículo (indice_h, percentil_scopus, jcr): métricas
  informativas exibidas na tela de detalhes; NÃO alimentam a RL05 (US-VQ04/VQ05).
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

VehicleType = Literal["evento", "revista"]

RelevanceLevel = Literal["A1", "A2", "A3", "A4", "B1", "B2", "SC"]

# Escala monotônica canônica da RL05 (decisão R1/R4, issue #133): estritamente
# decrescente — um nível superior sempre pondera mais que um inferior. 'SC'
# (Sem Classificação) é o peso de fallback para veículo sem nível configurado.
PESO_POR_NIVEL: dict[RelevanceLevel, float] = {
    "A1": 1.0,
    "A2": 0.85,
    "A3": 0.7,
    "A4": 0.55,
    "B1": 0.4,
    "B2": 0.3,
    "SC": 0.2,
}


class VehicleCreate(BaseModel):
    nome: str
    tipo: VehicleType
    sigla: str | None = None
    issn: str | None = None
    nivel: RelevanceLevel
    # Métricas descritivas (US-VQ04/VQ05) — não alimentam a RL05. `jcr` só é
    # válido para tipo 'revista'; essa regra é verificada no VehicleService.
    indice_h: int | None = Field(default=None, ge=0)
    percentil_scopus: int | None = Field(default=None, ge=0, le=100)
    jcr: float | None = Field(default=None, gt=0)


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
    indice_h: int | None = None
    percentil_scopus: int | None = None
    jcr: float | None = None
