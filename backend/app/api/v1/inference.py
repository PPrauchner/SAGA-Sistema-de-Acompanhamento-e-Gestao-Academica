"""
Router FastAPI para o endpoint de inferência lógica detalhada.

Responsabilidades:
- GET /api/v1/inference/{student_id}: executa todas as inferências do motor lógico para
  o aluno (RL01 a RL05) via InferenceService e retorna resultado estruturado completo com:
  situacao_inferida, apto_defesa, creditos_validos, em_risco, checklist detalhado por item,
  atividades_elegiveis (IDs que passaram na RL04), pontuacoes_producoes (score, nivel, peso
  por produção via RL05) e fatos_usados[] para exibição na InferencePage.
  Aplica @requires_role('aluno' apenas próprio, 'orientador' apenas orientandos,
  'coordenacao') e @audit_operation.
"""

from fastapi import APIRouter, HTTPException

from backend.app.models.inference import InferenceResult
from backend.app.repositories.fixtures import FixtureRepository
from backend.app.services.inference_service import InferenceService, StudentNotFoundError

router = APIRouter()


def _build_inference_service() -> InferenceService:
    """Ponto ÚNICO de wiring de dados (#41).

    Trocar FixtureRepository pelo repositório real do Firestore quando a issue #41
    (Discentes) mergear — nenhum outro código precisa mudar.
    """
    return InferenceService(FixtureRepository())


# Ordem canônica de aspectos a aplicar quando A01/A02 e get_current_user estiverem prontos:
#   @requires_role('aluno', 'orientador', 'coordenacao')
#   @audit_operation
@router.get("/inference/{student_id}", response_model=InferenceResult)
async def get_inference(student_id: str) -> InferenceResult:
    """Retorna o resultado completo da inferência lógica do aluno."""
    try:
        return await _build_inference_service().evaluate_student(student_id)
    except StudentNotFoundError:
        raise HTTPException(status_code=404, detail="Aluno não encontrado")
