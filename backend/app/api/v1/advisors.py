"""
Router FastAPI para os endpoints de gestão de orientadores.

Responsabilidades:
- GET /api/v1/advisors: lista orientadores com contagem de orientandos ativos.
  Restrito a @requires_role('coordenacao').
- POST /api/v1/advisors: cria orientador e envia convite de primeiro acesso.
  Aplica @requires_role('coordenacao') e @audit_operation.
- PUT /api/v1/advisors/{advisor_id}: atualiza dados do orientador.
  Aplica @requires_role('coordenacao') e @audit_operation.
- DELETE /api/v1/advisors/{advisor_id}: remove orientador (verificando ausência de
  orientandos ativos). Aplica @requires_role('coordenacao') e @audit_operation.
"""

from fastapi import APIRouter
from fastapi import Depends
from fastapi import status

from backend.app.aspects.audit import audit_operation
from backend.app.aspects.authorization import (
    requires_role,
)
from backend.app.core.auth import (
    CurrentUser,
    get_current_user,
)
from backend.app.models.advisor import (
    AdvisorCreateRequest,
    AdvisorUpdateRequest,
)
from backend.app.services.advisor_service import (
    AdvisorService,
)

router = APIRouter()

service = AdvisorService()


@router.get("/advisors")
@requires_role("coordenacao")
async def list_advisors(
    user: CurrentUser = Depends(
        get_current_user,
    ),
) -> list[dict]:
    return await service.list_advisors()


@router.get("/advisors/{advisor_id}")
@requires_role("coordenacao")
async def get_advisor(
    advisor_id: str,
    user: CurrentUser = Depends(
        get_current_user,
    ),
) -> dict:
    return await service.get_advisor(
        advisor_id,
    )


@router.post(
    "/advisors",
    status_code=status.HTTP_201_CREATED,
)
@requires_role("coordenacao")
@audit_operation
async def create_advisor(
    body: AdvisorCreateRequest,
    user: CurrentUser = Depends(
        get_current_user,
    ),
) -> dict:
    return await service.create_advisor(
        body,
        user,
    )


@router.put("/advisors/{advisor_id}")
@requires_role("coordenacao")
@audit_operation
async def update_advisor(
    advisor_id: str,
    body: AdvisorUpdateRequest,
    user: CurrentUser = Depends(
        get_current_user,
    ),
) -> dict:
    return await service.update_advisor(
        advisor_id,
        body,
        user,
    )


@router.delete("/advisors/{advisor_id}")
@requires_role("coordenacao")
@audit_operation
async def delete_advisor(
    advisor_id: str,
    user: CurrentUser = Depends(
        get_current_user,
    ),
) -> dict:
    return await service.delete_advisor(
        advisor_id,
        user,
    )
