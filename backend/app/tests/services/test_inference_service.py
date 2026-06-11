import pytest
from unittest.mock import AsyncMock, patch
from backend.app.models.program_config import ProgramConfig
from backend.app.services.inference_service import InferenceService
from backend.inference_engine.terms import Compound, Atom

@pytest.fixture
def mock_program_config():
    return {
        "id": "prog_test",
        "creditos_grupo_basico_min": 12,
        "creditos_grupo_especifico_min": 8,
        "creditos_grupo_tecnologico_max": 4,
        "creditos_total_min": 24,
        "meses_ate_qualificacao": 12,
        "max_prorrogacoes": 1,
        "duracao_prorrogacao_meses": 6,
        "niveis_veiculo": []
    }

@pytest.fixture
def anyio_backend():
    return 'asyncio'

@pytest.mark.anyio
@patch("backend.app.services.inference_service.ProgramRepository")
async def test_load_program_facts(mock_repo_class, mock_program_config):
    # Arrange
    mock_repo_instance = mock_repo_class.return_value
    mock_repo_instance.get_config = AsyncMock(return_value=mock_program_config)
    
    service = InferenceService()
    
    # Act
    facts = await service._load_program_facts("prog_test")
    
    # Assert
    mock_repo_instance.get_config.assert_called_with("prog_test")
    
    # Expected facts based on RL02 rules
    expected_facts = [
        Compound("min_creditos_basico", [Atom("prog_test"), Atom(12)]),
        Compound("min_creditos_especifico", [Atom("prog_test"), Atom(8)]),
        Compound("max_creditos_tecnologico", [Atom("prog_test"), Atom(4)]),
        Compound("min_creditos_total", [Atom("prog_test"), Atom(24)]),
    ]
    
    # Verify all expected facts are in the result
    for expected_fact in expected_facts:
        assert expected_fact in facts, f"Fato esperado {expected_fact} não encontrado na lista gerada."

@pytest.mark.anyio
@patch("backend.app.services.inference_service.InferenceEngine")
@patch("backend.app.services.inference_service.FactBase")
@patch("backend.app.services.inference_service.ProgramRepository")
async def test_run_inference(mock_repo_class, mock_fact_base_class, mock_engine_class, mock_program_config):
    # Arrange
    mock_repo_instance = mock_repo_class.return_value
    mock_repo_instance.get_config = AsyncMock(return_value=mock_program_config)
    
    mock_engine_instance = mock_engine_class.return_value
    mock_engine_instance.query_bool.return_value = True # Supondo que tem créditos
    
    mock_fact_base_instance = mock_fact_base_class.return_value
    
    service = InferenceService()
    
    # Act
    result = await service.run_inference(student_id="aluno_1", programa_id="prog_test")
    
    # Assert
    # 1. Verificamos se o repositório foi chamado
    mock_repo_instance.get_config.assert_called_with("prog_test")
    
    # 2. Verificamos se os fatos foram adicionados na FactBase
    assert mock_fact_base_instance.add_fact.called
    
    # 3. Verificamos se o motor foi instanciado
    mock_engine_class.assert_called()
    
    # 4. Verificamos se a query creditos_validos foi executada
    mock_engine_instance.query_bool.assert_called()
    query_term = mock_engine_instance.query_bool.call_args[0][0]
    assert query_term.functor == "creditos_validos"
    assert query_term.args[0].value == "aluno_1"
    
    # 5. O resultado deve conter o retorno da query
    assert result["creditos_validos"] is True
