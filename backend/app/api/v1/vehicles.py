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
"""

from fastapi import APIRouter

router = APIRouter()
