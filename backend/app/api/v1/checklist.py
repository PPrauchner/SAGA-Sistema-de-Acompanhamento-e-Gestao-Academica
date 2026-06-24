"""
Router FastAPI para o endpoint de checklist de integralização.

Responsabilidades:
- GET /api/v1/checklist/{student_id}: executa o motor lógico via ChecklistService →
  InferenceService e retorna o checklist completo com status de cada um dos 7 requisitos
  (créditos mínimos, créditos por grupo básico/específico/tecnológico, proficiência,
  qualificação, produção validada e plano concluído). Persiste snapshot imutável em
  students/{id}/inferred_status/. Aplica @requires_role para aluno (próprio), orientador
  (orientandos) e coordenação, além de @check_deadlines para garantir que fatos de prazo
  estejam atualizados antes da inferência.
"""

from fastapi import APIRouter, Depends, HTTPException

from backend.app.aspects.authorization import requires_role
from backend.app.core.auth import CurrentUser, get_current_user
from backend.app.models.checklist import ChecklistResponse
from backend.app.repositories.inference_repository import InferenceRepository
from backend.app.services.checklist_service import ChecklistService
from backend.app.services.inference_service import (
    InferenceService,
    StudentNotFoundError,
)

router = APIRouter()


def _get_checklist_service() -> ChecklistService:
    repo = InferenceRepository()
    return ChecklistService(InferenceService(repo), repo)


@router.get("/checklist/{student_id}", response_model=ChecklistResponse)
@requires_role("aluno", "orientador", "coordenacao")
async def get_checklist(
    student_id: str,
    user: CurrentUser = Depends(get_current_user),
    service: ChecklistService = Depends(_get_checklist_service),
) -> ChecklistResponse:
    """Retorna o checklist de integralização do aluno."""
    try:
        return await service.get_checklist(student_id)
    except StudentNotFoundError:
        raise HTTPException(status_code=404, detail="Aluno não encontrado")
