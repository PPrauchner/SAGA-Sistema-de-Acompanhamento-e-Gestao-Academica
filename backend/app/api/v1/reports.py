"""
Router FastAPI para os endpoints de relatórios gerenciais — exclusivos da coordenação.

Responsabilidades:
- GET /api/v1/reports/students-at-risk: alunos com situação de risco inferida pelo motor.
  Aplica @requires_role('coordenacao') e @audit_operation.
- GET /api/v1/reports/students-by-status: contagem e lista de alunos por situação registrada.
- GET /api/v1/reports/students-by-advisor: alunos agrupados por orientador com distribuição
  de status.
- GET /api/v1/reports/completion-time: tempo médio de integralização dos alunos concluídos
  (média de data_conclusao - data_ingresso).
- GET /api/v1/reports/productions: produção bibliográfica por aluno e por orientador com
  pontuação total e distribuição por nível de relevância. Aplica @audit_operation.
Sem lógica de negócio — cada endpoint apenas recebe a request, delega ao ReportService e
retorna a response.
"""

from fastapi import APIRouter, Depends

from backend.app.aspects.audit import audit_operation
from backend.app.aspects.authorization import requires_role
from backend.app.core.auth import CurrentUser, get_current_user
from backend.app.models.report import (
    CompletionTimeResponse,
    ProductionsReportResponse,
    StudentsAtRiskResponse,
    StudentsByAdvisorResponse,
    StudentsByStatusResponse,
)
from backend.app.services.report_service import ReportService

router = APIRouter()

service = ReportService()


@router.get("/reports/students-at-risk", response_model=StudentsAtRiskResponse)
@requires_role("coordenacao")
@audit_operation
async def get_students_at_risk(
    user: CurrentUser = Depends(get_current_user),
) -> StudentsAtRiskResponse:
    return await service.get_students_at_risk()


@router.get("/reports/students-by-status", response_model=StudentsByStatusResponse)
@requires_role("coordenacao")
async def get_students_by_status(
    user: CurrentUser = Depends(get_current_user),
) -> StudentsByStatusResponse:
    return await service.get_students_by_status()


@router.get("/reports/students-by-advisor", response_model=StudentsByAdvisorResponse)
@requires_role("coordenacao")
async def get_students_by_advisor(
    user: CurrentUser = Depends(get_current_user),
) -> StudentsByAdvisorResponse:
    return await service.get_students_by_advisor()


@router.get("/reports/completion-time", response_model=CompletionTimeResponse)
@requires_role("coordenacao")
async def get_completion_time(
    user: CurrentUser = Depends(get_current_user),
) -> CompletionTimeResponse:
    return await service.get_completion_time_avg()


@router.get("/reports/productions", response_model=ProductionsReportResponse)
@requires_role("aluno", "coordenacao")
@audit_operation
async def get_productions_report(
    user: CurrentUser = Depends(get_current_user),
) -> ProductionsReportResponse:
    return await service.get_productions_report(user.programa_id, user.role, user.uid)
