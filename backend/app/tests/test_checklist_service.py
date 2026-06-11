"""
Testes do ChecklistService sobre o FixtureRepository (issue #43).

Cobre a montagem dos 8 requisitos e a detecção de conflito situacao_registrada !=
situacao_inferida.
"""

import pytest

from backend.app.repositories.fixtures import FixtureRepository
from backend.app.services.checklist_service import ChecklistService
from backend.app.services.inference_service import InferenceService


@pytest.fixture
def checklist_service() -> ChecklistService:
    repo = FixtureRepository()
    return ChecklistService(InferenceService(repo), repo)


async def test_checklist_sem_conflito(checklist_service: ChecklistService) -> None:
    response = await checklist_service.get_checklist("aluno_apto")
    assert response.situacao_registrada == "fase_defesa"
    assert response.situacao_inferida == "fase_defesa"
    assert response.conflito_situacao is False
    assert response.apto_defesa is True
    # 7 requisitos presentes e todos cumpridos para o aluno apto.
    assert response.requisitos.creditos_minimos.status == "cumprido"
    assert response.requisitos.producao_validada.status == "cumprido"
    assert response.requisitos.producao_validada.quantidade_aprovadas == 1
    assert response.snapshot_id != ""


async def test_checklist_com_conflito(checklist_service: ChecklistService) -> None:
    response = await checklist_service.get_checklist("aluno_risco")
    # Registrada como 'regular', mas o motor infere 'em_risco'.
    assert response.situacao_registrada == "regular"
    assert response.situacao_inferida == "em_risco"
    assert response.conflito_situacao is True
    assert response.riscos_detectados
    assert response.requisitos.plano_concluido.tasks_total_nao_defesa == 3


async def test_checklist_requisitos_com_descricao(checklist_service: ChecklistService) -> None:
    response = await checklist_service.get_checklist("aluno_regular")
    assert "créditos totais" in response.requisitos.creditos_minimos.descricao
    assert response.requisitos.creditos_grupo_tecnologico.maximo == 4
