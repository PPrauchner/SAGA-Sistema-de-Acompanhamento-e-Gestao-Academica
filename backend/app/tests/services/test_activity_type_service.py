"""
Testes para ActivityTypeService.

Responsabilidades:
- Verificar a lógica de negócio para gestão de tipos de atividades.
- Garantir a interação correta com o ActivityTypeRepository.
"""

import os
from unittest.mock import AsyncMock, patch, ANY

# Configurar variáveis de ambiente dummy para satisfazer pydantic-settings
os.environ["FIREBASE_PROJECT_ID"] = "test-project"
os.environ["FIREBASE_PRIVATE_KEY"] = "test-key"
os.environ["FIREBASE_CLIENT_EMAIL"] = "test-email"

import pytest
from backend.app.services.activity_type_service import ActivityTypeService
from backend.app.models.activity_type import ActivityTypeCreate, ActivityTypeUpdate


@pytest.fixture
def mock_repo():
    """Fixture para ActivityTypeRepository mockado."""
    return AsyncMock()


@pytest.fixture
def service(mock_repo):
    """Fixture para ActivityTypeService com repositório mockado."""
    return ActivityTypeService(repository=mock_repo)


@pytest.mark.anyio
async def test_get_all_by_program(service, mock_repo):
    """Deve buscar tipos de atividade do repositório."""
    # Configuração do mock
    mock_repo.get_all_by_program.return_value = [{"id": "1", "nome": "Artigo"}]

    result = await service.get_all_by_program("prog_default")

    assert len(result) == 1
    assert result[0]["nome"] == "Artigo"
    mock_repo.get_all_by_program.assert_called_with("prog_default")


@pytest.mark.anyio
async def test_create_type_calls_repo(service, mock_repo):
    """Deve chamar o repositório para criar o tipo de atividade."""
    # Configuração
    data = ActivityTypeCreate(
        nome="Patente",
        categoria="tecnologico",
        pontuacao_base=5.0,
        programa_id="prog_default"
    )
    mock_repo.create_type.return_value = "new_id"

    result = await service.create_type(data)

    assert result == "new_id"
    mock_repo.create_type.assert_called_once()


@pytest.mark.anyio
async def test_toggle_active_switches_status(service, mock_repo):
    """Deve buscar o status atual e alterná-lo."""
    mock_repo.get_type.return_value = {"id": "1", "ativo": True}
    mock_repo.update_type.return_value = True

    result = await service.toggle_active("1")

    assert result is True
    mock_repo.update_type.assert_called_with("1", {"ativo": False, "atualizado_em": ANY})
