"""
Router FastAPI para os pesos Qualis versionados por programa (config da coordenação).

Responsabilidades:
- POST /api/v1/qualis-weights: coordenação define os pesos do próprio programa; cada chamada
  cria uma nova versão vigente sem sobrescrever a anterior. Aplica @requires_role('coordenacao')
  e @audit_operation (A02).
- GET /api/v1/qualis-weights: retorna o conjunto de pesos vigente do programa.
- GET /api/v1/qualis-weights/history: retorna o histórico de versões, visível à coordenação.

O programa é sempre o do usuário autenticado — a configuração fica restrita ao próprio
programa por construção.
"""

from fastapi import APIRouter, Depends, status

from backend.app.aspects.audit import audit_operation
from backend.app.aspects.authorization import requires_role
from backend.app.core.auth import CurrentUser, get_current_user
from backend.app.models.qualis_weights import QualisWeightsUpdate
from backend.app.services.qualis_weights_service import QualisWeightsService

router = APIRouter()


def get_qualis_weights_service() -> QualisWeightsService:
    """Provider do QualisWeightsService.

    O construtor do service tem parâmetros injetáveis (ex.: names), incompatíveis com a
    inspeção de dependência do FastAPI se usado diretamente em Depends; este provider
    isola essa construção.
    """
    return QualisWeightsService()


@router.post("/qualis-weights", status_code=status.HTTP_201_CREATED)
@requires_role("coordenacao")
@audit_operation
async def set_qualis_weights(
    body: QualisWeightsUpdate,
    user: CurrentUser = Depends(get_current_user),
    service: QualisWeightsService = Depends(get_qualis_weights_service),
) -> dict:
    return await service.set_weights(user.programa_id, user.uid, body)


@router.get("/qualis-weights")
@requires_role("coordenacao")
async def get_qualis_weights(
    user: CurrentUser = Depends(get_current_user),
    service: QualisWeightsService = Depends(get_qualis_weights_service),
) -> dict:
    return await service.get_active_weights(user.programa_id)


@router.get("/qualis-weights/history")
@requires_role("coordenacao")
async def get_qualis_weights_history(
    user: CurrentUser = Depends(get_current_user),
    service: QualisWeightsService = Depends(get_qualis_weights_service),
) -> list[dict]:
    return await service.list_history(user.programa_id)
