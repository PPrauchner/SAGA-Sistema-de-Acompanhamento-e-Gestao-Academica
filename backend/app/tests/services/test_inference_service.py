"""
Testes para InferenceService.

Responsabilidades:
- Verificar a integração entre o motor de inferência e a carga de dados.
- Garantir que mudanças nas configurações do programa (Issue #47) reflitam no status do aluno.
"""

import pytest
from unittest.mock import patch
from backend.app.services.inference_service import InferenceService
from backend.app.repositories.fixtures import FixtureRepository, _PROGRAM

@pytest.fixture
def anyio_backend():
    return 'asyncio'

@pytest.mark.anyio
async def test_inference_reflects_program_config_change(monkeypatch):
    """
    Testa se a mudança na configuração do programa (Issue #47) altera a situação inferida.
    Cenário: aluno_regular tem 25 créditos totais (14 basico, 9 especifico, 2 tecnologico).
    Com min_creditos_total=24 (padrão) -> Regular.
    Com min_creditos_total=30 (nova config) -> Em Risco.
    """
    # 1. Setup com configuração padrão (24 créditos mínimos)
    # _PROGRAM em fixtures.py já tem min_creditos_total=24
    repo = FixtureRepository()
    service = InferenceService(data_source=repo)
    
    # 2. Primeira inferência: deve ser 'qualificado' (pois o fixture aluno_regular já qualificou)
    result_before = await service.run_inference(student_id="aluno_regular", programa_id="prog_default")
    assert result_before.situacao_inferida == "qualificado"
    assert result_before.creditos_validos is True
    assert result_before.em_risco is False
    
    # 3. Alterar configuração do programa (Simulando Issue #47)
    # Usamos monkeypatch para alterar a constante no módulo de fixtures durante o teste
    monkeypatch.setitem(_PROGRAM, "min_creditos_total", 30)
    
    # 4. Segunda inferência: deve ser 'em_risco' pois o aluno tem apenas 25 créditos
    result_after = await service.run_inference(student_id="aluno_regular", programa_id="prog_default")
    
    # 5. Asserções
    assert result_after.situacao_inferida == "em_risco"
    assert result_after.creditos_validos is False
    assert result_after.em_risco is True
    assert any("Créditos insuficientes (25/30)" in msg for msg in result_after.riscos_detectados)

@pytest.mark.anyio
async def test_aptidao_defesa_aluno_apto():
    """Verifica se o aluno_apto é inferido corretamente como fase_defesa."""
    repo = FixtureRepository()
    service = InferenceService(data_source=repo)
    
    result = await service.run_inference(student_id="aluno_apto", programa_id="prog_default")
    
    assert result.situacao_inferida == "fase_defesa"
    assert result.apto_defesa is True
    assert result.checklist.creditos_minimos.status == "cumprido"
    assert result.checklist.producao_validada.status == "cumprido"

@pytest.mark.anyio
async def test_inference_with_non_existent_student():
    """Garante que o serviço levanta erro para aluno inexistente."""
    from backend.app.services.inference_service import StudentNotFoundError
    
    repo = FixtureRepository()
    service = InferenceService(data_source=repo)
    
    with pytest.raises(StudentNotFoundError):
        await service.run_inference(student_id="inexistente", programa_id="prog_default")
