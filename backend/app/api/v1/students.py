"""
Router FastAPI para os endpoints de gestão de discentes.

Responsabilidades:
- GET /api/v1/students: lista alunos com filtros opcionais de status, orientador_id e
  programa_id. Coordenação vê todos; orientador vê apenas próprios orientandos.
  Aplica @check_deadlines para recalcular status de prazo na listagem.
- GET /api/v1/students/{student_id}: detalhe do aluno. Aluno vê apenas o próprio.
- POST /api/v1/students: cria aluno e dispara convite de primeiro acesso.
  Aplica @requires_role('coordenacao') e @audit_operation.
- PUT /api/v1/students/{student_id}: atualiza dados editáveis do aluno.
  Aplica @requires_role('coordenacao') e @audit_operation.
- PATCH /api/v1/students/{student_id}/qualificacao: registra aprovação na qualificação,
  gerando fato qualificacao_aprovada para o motor. Aplica @track_history.
- PATCH /api/v1/students/{student_id}/proficiencia: registra comprovação de proficiência.
  Aplica @track_history.
- PATCH /api/v1/students/{student_id}/situacao: atualiza situação registrada manualmente.
  Aplica @track_history.
"""

from fastapi import APIRouter, Depends, status

from backend.app.aspects.audit import audit_operation
from backend.app.aspects.authorization import requires_role
from backend.app.aspects.history import track_history
from backend.app.core.auth import CurrentUser, get_current_user
from backend.app.models.student import (
    ProficienciaRequest,
    QualificacaoRequest,
    SituacaoRequest,
    StudentCreateRequest,
    StudentResponse,
    StudentUpdateRequest,
)
from backend.app.services.student_service import StudentService

router = APIRouter()

service = StudentService()


@router.get("/students", response_model=list[StudentResponse])
@requires_role("coordenacao", "orientador")
async def list_students(
    user: CurrentUser = Depends(get_current_user),
) -> list[StudentResponse]:
    return await service.list_students(user)


@router.get("/students/{student_id}", response_model=StudentResponse)
@requires_role("coordenacao", "orientador", "aluno")
async def get_student(
    student_id: str,
    user: CurrentUser = Depends(get_current_user),
) -> StudentResponse:
    return await service.get_student(student_id, user)


@router.post(
    "/students",
    status_code=status.HTTP_201_CREATED,
)
@requires_role("coordenacao")
@audit_operation
async def create_student(
    body: StudentCreateRequest,
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    return await service.create_student(body, user)


@router.put("/students/{student_id}")
@requires_role("coordenacao")
@audit_operation
async def update_student(
    student_id: str,
    body: StudentUpdateRequest,
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    return await service.update_student(student_id, body, user)


@router.delete("/students/{student_id}")
@requires_role("coordenacao")
@audit_operation
async def delete_student(
    student_id: str,
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    return await service.delete_student(student_id, user)


@router.patch("/students/{student_id}/qualificacao")
@requires_role("coordenacao")
@audit_operation
@track_history
async def update_qualificacao(
    student_id: str,
    body: QualificacaoRequest,
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    return await service.update_qualificacao(
        student_id,
        body,
        user,
    )


@router.patch("/students/{student_id}/proficiencia")
@requires_role("coordenacao")
@audit_operation
@track_history
async def update_proficiencia(
    student_id: str,
    body: ProficienciaRequest,
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    return await service.update_proficiencia(
        student_id,
        body,
        user,
    )


@router.patch("/students/{student_id}/situacao")
@requires_role("coordenacao")
@audit_operation
@track_history
async def update_situacao(
    student_id: str,
    body: SituacaoRequest,
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    return await service.update_situacao(
        student_id,
        body,
        user,
    )
