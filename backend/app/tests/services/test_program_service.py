"""
Testes para ProgramService.

Responsabilidades:
- Verificar a lógica de negócio para configurações de programas.
- Garantir a interação correta com o ProgramRepository.
"""

import os
from unittest.mock import AsyncMock, patch

os.environ["FIREBASE_PROJECT_ID"] = "test-project"
os.environ["FIREBASE_PRIVATE_KEY"] = "test-key"
os.environ["FIREBASE_CLIENT_EMAIL"] = "test-email"

import pytest
from backend.app.services.program_service import ProgramService
from backend.app.models.program_config import ProgramConfigUpdate


@pytest.fixture
def mock_repo():
    """Fixture para ProgramRepository mockado."""
    return AsyncMock()


@pytest.fixture
def service(mock_repo):
    """Fixture para ProgramService com repositório mockado."""
    return ProgramService(repository=mock_repo)


@pytest.mark.anyio
async def test_get_config_returns_model(service, mock_repo):
    """Deve buscar a configuração do repositório e retornar como dicionário."""
    mock_repo.get_config.return_value = {
        "id": "prog_default",
        "creditos_grupo_basico_min": 12,
        "creditos_grupo_especifico_min": 8,
        "creditos_grupo_tecnologico_max": 4,
        "creditos_total_min": 24,
        "max_prorrogacoes": 1,
        "duracao_prorrogacao_meses": 6,
        "meses_ate_qualificacao": 12
    }

    result = await service.get_config("prog_default")

    assert result["creditos_total_min"] == 24
    mock_repo.get_config.assert_called_with("prog_default")


@pytest.mark.anyio
async def test_update_config_calls_repo(service, mock_repo):
    """Deve chamar o repositório para atualizar a configuração com dados validados."""
    update_data = ProgramConfigUpdate(creditos_total_min=30)
    mock_repo.update_config.return_value = True

    result = await service.update_config("prog_default", update_data)

    assert result is True
    mock_repo.update_config.assert_called_once()
    # Verifica se passou o dicionário, não o modelo
    args, _ = mock_repo.update_config.call_args
    assert args[1] == {"creditos_total_min": 30}

