"""
Testes do ChecklistService sobre o FixtureRepository (issue #43).

Cobre a montagem dos 8 requisitos e a detecção de conflito situacao_registrada !=
situacao_inferida.
"""

import pytest

from backend.app.models.inference import (
    CreditoMaximoItem,
    CreditoMinimoItem,
    InferenceChecklist,
    InferenceResult,
    StatusItem,
)
from backend.app.repositories.fixtures import FixtureRepository
from backend.app.services.checklist_service import ChecklistService
from backend.app.services.inference_service import InferenceService


@pytest.fixture
def checklist_service() -> ChecklistService:
    repo = FixtureRepository()
    return ChecklistService(InferenceService(repo), repo)


@pytest.mark.anyio
async def test_checklist_sem_conflito(checklist_service: ChecklistService) -> None:
    response = await checklist_service.get_checklist("aluno_apto")
    assert response.situacao_registrada == "em_fase_de_defesa"
    assert response.situacao_inferida == "em_fase_de_defesa"
    assert response.conflito_situacao is False
    assert response.apto_defesa is True
    # 7 requisitos presentes e todos cumpridos para o aluno apto.
    assert response.requisitos.creditos_minimos.status == "cumprido"
    assert response.requisitos.producao_validada.status == "cumprido"
    assert response.requisitos.producao_validada.quantidade_aprovadas == 1
    assert response.snapshot_id != ""


@pytest.mark.anyio
async def test_checklist_com_conflito(checklist_service: ChecklistService) -> None:
    response = await checklist_service.get_checklist("aluno_risco")
    # Registrada como 'regular', mas o motor infere 'em_risco'.
    assert response.situacao_registrada == "regular"
    assert response.situacao_inferida == "em_risco"
    assert response.conflito_situacao is True
    assert response.riscos_detectados
    assert response.requisitos.plano_concluido.tasks_total_nao_defesa == 3


@pytest.mark.anyio
async def test_checklist_requisitos_com_descricao(checklist_service: ChecklistService) -> None:
    response = await checklist_service.get_checklist("aluno_regular")
    assert "créditos totais" in response.requisitos.creditos_minimos.descricao
    assert response.requisitos.creditos_grupo_tecnologico.maximo == 4


@pytest.mark.anyio
async def test_aluno_recem_todos_nao_cumpridos_pendente(checklist_service: ChecklistService) -> None:
    """Aluno no primeiro dia: nenhum flag de risco deve disparar → todos "pendente"."""
    response = await checklist_service.get_checklist("aluno_recem")
    assert response.situacao_inferida == "regular"
    assert response.requisitos.creditos_minimos.status == "pendente"
    assert response.requisitos.creditos_grupo_basico.status == "pendente"
    assert response.requisitos.creditos_grupo_especifico.status == "pendente"
    assert response.requisitos.proficiencia.status == "pendente"
    assert response.requisitos.qualificacao.status == "pendente"
    assert response.requisitos.producao_validada.status == "pendente"
    assert response.requisitos.plano_concluido.status == "pendente"


@pytest.mark.anyio
async def test_aluno_credito_risco_itens_credito_em_risco(checklist_service: ChecklistService) -> None:
    """Aluno na metade do prazo sem créditos: itens de crédito "em_risco", demais "pendente"."""
    response = await checklist_service.get_checklist("aluno_credito_risco")
    assert response.requisitos.creditos_minimos.status == "em_risco"
    assert response.requisitos.creditos_grupo_basico.status == "em_risco"
    assert response.requisitos.creditos_grupo_especifico.status == "em_risco"
    assert response.requisitos.proficiencia.status == "cumprido"
    assert response.requisitos.qualificacao.status == "cumprido"
    assert response.requisitos.producao_validada.status == "pendente"
    assert response.requisitos.plano_concluido.status == "pendente"


@pytest.mark.anyio
async def test_aluno_qual_risco_qualificacao_em_risco(checklist_service: ChecklistService) -> None:
    """Qualificação pendente com prazo < 90 dias: qualificacao "em_risco", créditos cumpridos."""
    response = await checklist_service.get_checklist("aluno_qual_risco")
    assert response.requisitos.qualificacao.status == "em_risco"
    assert response.requisitos.creditos_minimos.status == "cumprido"
    assert response.requisitos.plano_concluido.status == "cumprido"


@pytest.mark.anyio
async def test_aluno_plano_risco_plano_em_risco(checklist_service: ChecklistService) -> None:
    """Plano 0% concluído com ~75% do prazo decorrido: plano_concluido "em_risco"."""
    response = await checklist_service.get_checklist("aluno_plano_risco")
    assert response.requisitos.plano_concluido.status == "em_risco"
    assert response.requisitos.creditos_minimos.status == "cumprido"
    assert response.requisitos.qualificacao.status == "cumprido"


@pytest.mark.anyio
async def test_aluno_prazo_expirado_todos_pendentes_em_risco(checklist_service: ChecklistService) -> None:
    """Prazo expirado: proficiência e produção (sem cláusula própria) ficam "em_risco"."""
    response = await checklist_service.get_checklist("aluno_risco")
    assert response.requisitos.proficiencia.status == "em_risco"
    assert response.requisitos.producao_validada.status == "em_risco"
    assert response.requisitos.creditos_minimos.status == "em_risco"


class _FakeInference:
    async def run_inference(self, student_id: str, programa_id: str) -> InferenceResult:
        return InferenceResult(
            student_id=student_id,
            programa_id=programa_id,
            timestamp="2026-07-10T00:00:00Z",
            situacao_inferida="qualificado",
            apto_defesa=False,
            creditos_validos=True,
            em_risco=False,
            checklist=InferenceChecklist(
                creditos_minimos=CreditoMinimoItem(status="cumprido", obtidos=24, minimo=24),
                creditos_grupo_basico=CreditoMinimoItem(status="cumprido", obtidos=12, minimo=12),
                creditos_grupo_especifico=CreditoMinimoItem(status="cumprido", obtidos=8, minimo=8),
                creditos_grupo_tecnologico=CreditoMaximoItem(status="cumprido", obtidos=4, maximo=4),
                proficiencia=StatusItem(status="cumprido"),
                qualificacao=StatusItem(status="cumprido"),
                producao_validada=StatusItem(status="pendente"),
                plano_concluido=StatusItem(status="pendente"),
            ),
            atividades_elegiveis=[],
            pontuacoes_producoes=[],
            fatos_usados=[],
            snapshot_id="snap1",
        )


class _FakeChecklistData:
    async def get_student(self, student_id: str):
        return {
            "id": student_id,
            "nome": "Aluno",
            "programa_id": "prog",
            "situacao_registrada": "qualificado",
            "proficiencia_data": "2026-04-01T00:00:00Z",
            "proficiencia_comprovante_url": "https://example.com/prof.pdf",
            "qualificacao_data": "2026-05-01T00:00:00Z",
            "qualificacao_comprovante_url": "https://example.com/qual.pdf",
        }

    async def get_approved_productions(self, student_id: str):
        return []

    async def get_plan_tasks(self, student_id: str):
        return []


@pytest.mark.anyio
async def test_checklist_inclui_comprovantes_de_proficiencia_e_qualificacao() -> None:
    service = ChecklistService(_FakeInference(), _FakeChecklistData())

    response = await service.get_checklist("student1")

    assert response.requisitos.proficiencia.data_comprovacao == "2026-04-01T00:00:00Z"
    assert response.requisitos.proficiencia.comprovante_url == "https://example.com/prof.pdf"
    assert response.requisitos.qualificacao.data_aprovacao == "2026-05-01T00:00:00Z"
    assert response.requisitos.qualificacao.comprovante_url == "https://example.com/qual.pdf"
