"""
Testes para ProgramService.

Responsabilidades:
- Verificar a lógica de negócio para configurações de programas.
- Garantir a interação correta com o ProgramRepository.
"""

import os
from unittest.mock import AsyncMock

os.environ["FIREBASE_PROJECT_ID"] = "test-project"
os.environ["FIREBASE_PRIVATE_KEY"] = "test-key"
os.environ["FIREBASE_CLIENT_EMAIL"] = "test-email"

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from backend.app.services.program_service import ProgramService
from backend.app.models.program_config import ProgramConfigUpdate


VALID_CONFIG = {
    "id": "prog_default",
    "creditos_grupo_basico_min": 8,
    "creditos_grupo_especifico_min": 4,
    "creditos_grupo_tecnologico_max": 4,
    "creditos_total_min": 12,
    "max_prorrogacoes": 1,
    "duracao_prorrogacao_meses": 6,
    "meses_ate_qualificacao": 24,
}


@pytest.fixture
def mock_repo():
    """Fixture para ProgramRepository mockado."""
    return AsyncMock()


@pytest.fixture
def service(mock_repo):
    """Fixture para ProgramService com repositório mockado."""
    return ProgramService(repository=mock_repo)


@pytest.mark.parametrize(
    "field",
    [
        "creditos_grupo_basico_min",
        "creditos_grupo_especifico_min",
        "creditos_grupo_tecnologico_max",
        "creditos_total_min",
    ],
)
@pytest.mark.parametrize("value", [-1, None, "", float("nan"), 1.5])
def test_program_config_update_rejeita_credito_invalido(field, value):
    with pytest.raises(ValidationError):
        ProgramConfigUpdate(**{field: value})


@pytest.mark.parametrize("value", [0, -1, None, "", float("nan"), 1.5])
def test_program_config_update_rejeita_meses_ate_qualificacao_invalido(value):
    with pytest.raises(ValidationError):
        ProgramConfigUpdate(meses_ate_qualificacao=value)

@pytest.mark.anyio
async def test_get_config_returns_model(service, mock_repo):
    """Deve buscar a configuração do repositório e retornar como dicionário."""
    mock_repo.get_config.return_value = VALID_CONFIG

    result = await service.get_config("prog_default")

    assert result["creditos_total_min"] == 12
    mock_repo.get_config.assert_called_with("prog_default")


@pytest.mark.anyio
async def test_update_config_calls_repo(service, mock_repo):
    """Deve chamar o repositório para atualizar a configuração com dados validados."""
    update_data = ProgramConfigUpdate(creditos_total_min=30)
    mock_repo.get_config.return_value = VALID_CONFIG
    mock_repo.update_config.return_value = True

    result = await service.update_config("prog_default", update_data)

    assert result is True
    mock_repo.update_config.assert_called_once()
    # Verifica se passou o dicionário, não o modelo
    args, _ = mock_repo.update_config.call_args
    assert args[1] == {"creditos_total_min": 30}


@pytest.mark.anyio
async def test_update_config_aceita_configuracao_valida(service, mock_repo):
    update_data = ProgramConfigUpdate(
        creditos_total_min=12,
        creditos_grupo_basico_min=8,
        creditos_grupo_especifico_min=4,
        meses_ate_qualificacao=24,
    )
    mock_repo.get_config.return_value = VALID_CONFIG
    mock_repo.update_config.return_value = True

    result = await service.update_config("prog_default", update_data)

    assert result is True
    mock_repo.update_config.assert_called_once()


@pytest.mark.anyio
async def test_update_config_rejeita_creditos_total_menor_que_basico_mais_especifico(service, mock_repo):
    update_data = ProgramConfigUpdate(
        creditos_total_min=10,
        creditos_grupo_basico_min=8,
        creditos_grupo_especifico_min=4,
    )
    mock_repo.get_config.return_value = VALID_CONFIG

    with pytest.raises(HTTPException) as exc:
        await service.update_config("prog_default", update_data)

    assert exc.value.status_code == 422
    assert "Créditos totais mínimos" in exc.value.detail
    mock_repo.update_config.assert_not_called()


@pytest.mark.anyio
async def test_update_config_rejeita_invariante_usando_config_atual(service, mock_repo):
    update_data = ProgramConfigUpdate(creditos_grupo_basico_min=9)
    mock_repo.get_config.return_value = VALID_CONFIG

    with pytest.raises(HTTPException):
        await service.update_config("prog_default", update_data)

    mock_repo.update_config.assert_not_called()
