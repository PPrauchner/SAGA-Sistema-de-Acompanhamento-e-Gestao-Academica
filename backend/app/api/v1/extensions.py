"""Router FastAPI para solicitacoes de prorrogacao."""

<<<<<<< HEAD
Responsabilidades:
- Gerenciar rotas de criação, parecer técnico e homologação final de prazos.
- Aplicar decoradores AOP estritamente nos join points definidos pelas especificações.
"""

from backend.app.aspects.audit import audit_operation
from backend.app.aspects.deadline_validation import check_deadlines
from backend.app.aspects.alerts import trigger_alerts
from backend.app.aspects.authorization import requires_role
from backend.app.core.auth import get_current_user, CurrentUser

# Correção C2/C4: Modelos corretos e payload alinhado
from backend.app.models.extension import (
    ExtensionCreateRequest,
    ReviewRequest,
    DecisionRequest,
    ExtensionResponse,
)
# Correção C2: Serviço no singular
from backend.app.services.extension_service import ExtensionService
from backend.app.services.tests.test_notification_service import service

router = APIRouter(
    tags=["Prorrogações"],
)

# Provedor local de dependência do serviço para evitar app.dependencies inexistente
async def get_extension_service() -> ExtensionService:
    return ExtensionService()

AuthUser = Annotated[CurrentUser, Depends(get_current_user)]
Service     = Annotated[ExtensionService, Depends(get_extension_service)]

# ---------------------------------------------------------------------------
# POST /api/v1/extensions
# ---------------------------------------------------------------------------
@router.post(
    "",
    response_model=ExtensionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Criar solicitação de prorrogação (aluno)",
)
@requires_role("aluno")
@audit_operation
@check_deadlines
@trigger_alerts
async def create_extension(
    payload: ExtensionCreateRequest,
    current_user: AuthUser,
    service: Service,
) -> ExtensionResponse:
    """Cria uma nova solicitação de prorrogação com status 'pendente'."""
    return await service.create_extension(
        student_id=current_user.uid,
        payload=payload,
        requesting_uid=current_user.uid,
    )

# ---------------------------------------------------------------------------
# PATCH /api/v1/extensions/{student_id}/{extension_id}/review
# ---------------------------------------------------------------------------
@router.patch(
    "/{student_id}/{extension_id}/review",
    response_model=ExtensionResponse,
    summary="Emitir parecer técnico (orientador)",
)
@requires_role("orientador")
@audit_operation
async def review_extension(
    student_id: str,
    extension_id: str,
    payload: ReviewRequest,
    current_user: AuthUser,
    service: Service,
) -> ExtensionResponse:
    """Permite ao orientador emitir o parecer técnico de uma prorrogação."""
    return await service.add_review(
        student_id=student_id,
        extension_id=extension_id,
        parecer=payload.parecer_orientador,
        orientador_uid=current_user.uid,
    )

# ---------------------------------------------------------------------------
# PATCH /api/v1/extensions/{student_id}/{extension_id}/approve (Spec 08 M1/C4)
# ---------------------------------------------------------------------------
@router.patch(
    "/{student_id}/{extension_id}/approve",
    response_model=ExtensionResponse,
    summary="Homologar decisão de prorrogação (coordenação)",
)
@requires_role("coordenacao")
@audit_operation
@check_deadlines
@trigger_alerts
async def decide_extension(
    student_id: str,
    extension_id: str,
    payload: DecisionRequest,
    current_user: AuthUser,
    service: Service,
) -> ExtensionResponse:
    """Processa o deferimento/indeferimento baseado na Spec 08 e contrato booleano."""
    # review_extension
    return await service.add_review(
        student_id=student_id,
        extension_id=extension_id,
        parecer=payload.parecer_orientador,
        orientador_uid=current_user.uid,
    )
# ---------------------------------------------------------------------------
# GET — Listagens e Dashboard (AOP mitigado para evitar M2)
# ---------------------------------------------------------------------------
@router.get(
    "/students/{student_id}",
    response_model=list[ExtensionResponse],
    summary="Listar prorrogações do aluno (Contrato Front C4)",
)
@requires_role("aluno", "coordenacao")
@audit_operation
async def list_student_extensions(
    student_id: str,
    current_user: AuthUser,
    service: Service,
) -> list[ExtensionResponse]:
    """Retorna o histórico completo de prorrogações de um discente."""
    return await service.list_by_student(student_id)

@router.get(
    "/dashboard",
    response_model=list[ExtensionResponse],
    summary="Dashboard de prorrogações pendentes (Contrato Front C4)",
)
@requires_role("orientador", "coordenacao")
@audit_operation
async def get_dashboard_extensions(
    current_user: AuthUser,
    service: Service,
) -> list[ExtensionResponse]:
    """Retorna as prorrogações aplicáveis ao contexto do painel do avaliador."""
    if current_user.role == "orientador":
        return await service.list_pending_for_advisor(
            current_user.uid
        )

    return await service.list_all_pending()
=======
from fastapi import APIRouter, Depends, status

from backend.app.aspects.audit import audit_operation
from backend.app.aspects.authorization import requires_role
from backend.app.core.auth import CurrentUser, get_current_user
from backend.app.models.extension import ExtensionCreateRequest, ExtensionResponse
from backend.app.services.extension_service import ExtensionService

router = APIRouter()

service = ExtensionService()


@router.get("/extensions", response_model=list[ExtensionResponse])
@requires_role("aluno", "orientador", "coordenacao")
async def list_extensions(
    user: CurrentUser = Depends(get_current_user),
) -> list[ExtensionResponse]:
    """Lista prorrogacoes visiveis para o usuario autenticado."""
    return await service.list_extensions(user)


@router.post(
    "/extensions",
    response_model=ExtensionResponse,
    status_code=status.HTTP_201_CREATED,
)
@requires_role("aluno", "orientador")
@audit_operation
async def create_extension(
    body: ExtensionCreateRequest,
    user: CurrentUser = Depends(get_current_user),
) -> ExtensionResponse:
    """Cria uma solicitacao de prorrogacao para aluno ou orientando."""
    return await service.create_extension(body, user)
>>>>>>> 0161ba8854c4238232217a8a4715b9d5484d34b9
