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

from fastapi import APIRouter, HTTPException

from backend.app.models.checklist import ChecklistResponse
from backend.app.repositories.fixtures import FixtureRepository
from backend.app.services.checklist_service import ChecklistService
from backend.app.services.inference_service import InferenceService, StudentNotFoundError

router = APIRouter()


def _build_checklist_service() -> ChecklistService:
    """Ponto ÚNICO de wiring de dados (#41).

    Trocar FixtureRepository pelos repositórios reais do Firestore quando a issue #41
    (Discentes) mergear — nenhum outro código precisa mudar.
    """
    repo = FixtureRepository()
    return ChecklistService(InferenceService(repo), repo)


# Ordem canônica de aspectos a aplicar quando A01/A04 e get_current_user estiverem prontos:
#   @requires_role('aluno', 'orientador', 'coordenacao')
#   @check_deadlines
@router.get("/checklist/{student_id}", response_model=ChecklistResponse)
async def get_checklist(student_id: str) -> ChecklistResponse:
    """Retorna o checklist de integralização do aluno."""
    try:
        return await _build_checklist_service().get_checklist(student_id)
    except StudentNotFoundError:
        raise HTTPException(status_code=404, detail="Aluno não encontrado")
