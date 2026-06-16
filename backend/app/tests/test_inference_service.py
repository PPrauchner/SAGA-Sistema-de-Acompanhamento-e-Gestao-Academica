"""
Testes do InferenceService sobre o FixtureRepository (costura de dados de #43).

Cobre os três cenários de situação inferida produzidos pelas fixtures:
- aluno_apto    → em_fase_de_defesa (apto_defesa, creditos_validos, sem risco).
- aluno_risco   → em_risco (prazo estourado + créditos insuficientes).
- aluno_regular → qualificado (créditos válidos, mas sem produção/plano concluído).
"""

import pytest

from backend.app.repositories.fixtures import FixtureRepository
from backend.app.services.inference_service import InferenceService, StudentNotFoundError


@pytest.fixture
def service() -> InferenceService:
    return InferenceService(FixtureRepository())


async def test_aluno_apto_em_fase_de_defesa(service: InferenceService):
    result = await service.run_inference("aluno_apto", "prog_default")
    assert result.apto_defesa is True
    assert result.creditos_validos is True
    assert result.em_risco is False
    assert result.situacao_inferida == "em_fase_de_defesa"
    assert result.snapshot_id != ""
    # Todas as 3 atividades são elegíveis (comprovante + tipo ativo + dentro do período).
    assert set(result.atividades_elegiveis) == {"atv_apto_b", "atv_apto_e", "atv_apto_t"}
    # Produção A1 com base 10 → score 20.0, peso 2.0.
    assert len(result.pontuacoes_producoes) == 1
    pontuacao = result.pontuacoes_producoes[0]
    assert pontuacao.score == 20.0
    assert pontuacao.peso_aplicado == 2.0
    assert pontuacao.nivel_veiculo == "A1"


async def test_aluno_risco_em_risco(service: InferenceService):
    result = await service.run_inference("aluno_risco", "prog_default")
    assert result.em_risco is True
    assert result.apto_defesa is False
    assert result.situacao_inferida == "em_risco"
    assert result.riscos_detectados  # ao menos um motivo de risco
    # Apenas a atividade com comprovante e tipo ativo é elegível.
    assert result.atividades_elegiveis == ["atv_risco_b"]


async def test_aluno_regular_qualificado(service: InferenceService):
    result = await service.run_inference("aluno_regular", "prog_default")
    assert result.apto_defesa is False
    assert result.em_risco is False
    assert result.creditos_validos is True
    assert result.situacao_inferida == "qualificado"
    # Sem produção bibliográfica → requisito de produção não cumprido.
    assert result.checklist.producao_validada.status != "cumprido"


async def test_aluno_inexistente(service: InferenceService):
    with pytest.raises(StudentNotFoundError):
        await service.run_inference("nao_existe", "prog_default")
