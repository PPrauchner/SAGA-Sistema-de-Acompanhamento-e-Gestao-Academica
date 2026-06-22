"""
Router FastAPI para os endpoints de produções bibliográficas.

Responsabilidades:
- GET /api/v1/productions: lista produções com pontuação calculada pelo motor RL05.
  Aluno vê as próprias; orientador vê dos orientandos; coordenação vê todas.
- POST /api/v1/productions: aluno registra produção bibliográfica. Motor RL05 calcula
  pontuação ponderada pelo nível de relevância do veículo imediatamente após o registro.
  Aplica @requires_role('aluno') e @audit_operation. (@check_deadlines deferido até o
  aspecto A04 ser implementado, conforme precedência dos demais routers.) Persiste
  pontuacao_calculada, nivel_veiculo e peso_aplicado no documento.
"""

from fastapi import APIRouter, Depends, status

from backend.app.aspects.audit import audit_operation
from backend.app.aspects.authorization import requires_role
from backend.app.core.auth import CurrentUser, get_current_user
from backend.app.models.production import ProductionCreate
from backend.app.services.production_service import ProductionService

router = APIRouter()


@router.get("/productions")
@requires_role("coordenacao", "orientador", "aluno")
async def list_productions(
    user: CurrentUser = Depends(get_current_user),
    service: ProductionService = Depends(ProductionService),
) -> list[dict]:
    return await service.list_productions(user)


@router.post(
    "/productions",
    status_code=status.HTTP_201_CREATED,
)
@requires_role("aluno")
@audit_operation
async def create_production(
    body: ProductionCreate,
    user: CurrentUser = Depends(get_current_user),
    service: ProductionService = Depends(ProductionService),
) -> dict:
    return await service.create_production(body, user)
