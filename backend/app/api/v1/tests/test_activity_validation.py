import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
from fastapi import HTTPException, status
from backend.app.models.activity import ActivityStatus, ValidateAction, ValidateActivityRequest
from backend.app.services.activity_service import emitir_parecer_orientador, validate_activity

@pytest.mark.asyncio
@patch("backend.app.services.activity_service._repo")
async def test_emitir_parecer_sucesso(mock_repo):
    # Arrange
    mock_repo.get_by_id.return_value = {"status": ActivityStatus.enviado, "id": "act_123"}
    mock_repo.update_by_id.return_value = {"id": "act_123", "status": ActivityStatus.enviado}
    
    payload = ValidateActivityRequest(
        acao=ValidateAction.parecer_orientador,
        parecer_orientador="Parecer favorável do orientador."
    )

    # Act
    response = await emitir_parecer_orientador("act_123", payload, "user_uid_1")

    # Assert
    assert response is not None
    mock_repo.update_by_id.assert_called_once()


@pytest.mark.asyncio
@patch("backend.app.services.activity_service._repo")
async def test_validate_activity_rejeitada_status_invalido(mock_repo):
    # Arrange
    mock_repo.get_by_id.return_value = {"status": ActivityStatus.aprovado, "id": "act_123"}
    payload = ValidateActivityRequest(acao=ValidateAction.rejeitar, observacao="Incompleto")

    # Act & Assert
    with pytest.raises(HTTPException) as exc:
        await validate_activity("act_123", payload, "coord_uid_1")
    assert exc.value.status_code == status.HTTP_409_CONFLICT


@pytest.mark.asyncio
@patch("backend.app.services.activity_service._repo")
@patch("backend.app.services.activity_service._type_repo")
@patch("backend.app.services.activity_service._student_repo")
@patch("backend.app.services.activity_service.InferenceService")
async def test_validate_activity_aprovar_com_teto_rl04(mock_inference, mock_student_repo, mock_type_repo, mock_repo):
    # Arrange
    # Simula atividade que gera 10 créditos, mas o teto da categoria é 12 e o aluno já tem 5 aprovados (Estoura o teto!)
    mock_repo.get_by_id.return_value = {
        "id": "act_123",
        "status": ActivityStatus.enviado,
        "creditos_gerados": 10.0,
        "student_id": "stud_1",
        "tipo_id": "tipo_1"
    }
    
    mock_type_repo.get.return_value = {
        "categoria": "basico",
        "limite_maximo_creditos": 12.0
    }
    
    # Mock para a função interna de créditos aprovados da classe ActivityService
    with patch("backend.app.services.activity_service.ActivityService._approved_credits_in_category", return_value=5.0):
        payload = ValidateActivityRequest(acao=ValidateAction.aprovar, observacao="Ok")
        
        # Act
        response = await validate_activity("act_123", payload, "coord_uid_1")
        
        # Assert
        # Teto (12) - Já Aprovados (5) = Concedidos deve ser exatamente 7.0 (Regra RL04 aplicada!)
        assert response.creditos_contabilizados == 7.0
        mock_repo.update_by_id.assert_called_once()