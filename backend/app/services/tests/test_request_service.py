from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from backend.app.core.auth import CurrentUser
from backend.app.services.request_service import RequestService


def _coord() -> CurrentUser:
    return CurrentUser(uid="coord", role="coordenacao", programa_id="prog1", email="c@x.com")

def _advisor() -> CurrentUser:
    return CurrentUser(uid="adv", role="orientador", programa_id="prog1", email="a@x.com")

@pytest.fixture
def mock_repos():
    with patch("backend.app.services.request_service.ActivityRepository") as mock_act, \
         patch("backend.app.services.request_service.ExtensionRepository") as mock_ext, \
         patch("backend.app.services.request_service.TransferRepository") as mock_tr, \
         patch("backend.app.services.request_service.CoordinationTransferRepository") as mock_coord_tr, \
         patch("backend.app.services.request_service.StudentRepository") as mock_stud, \
         patch("backend.app.services.request_service.AdvisorRepository") as mock_adv, \
         patch("backend.app.services.request_service.FirebaseRepository") as mock_fb:
        
        mock_adv.return_value.list_all = AsyncMock()
        mock_stud.return_value.list_all = AsyncMock()
        mock_coord_tr.return_value.query = AsyncMock()
        mock_fb.return_value.list_all = AsyncMock()
        mock_ext.return_value.list_all = AsyncMock()
        mock_tr.return_value.list_by_program = AsyncMock()
        mock_coord_tr.return_value.list_by_program = AsyncMock()

        yield {
            "act": mock_act.return_value,
            "ext": mock_ext.return_value,
            "tr": mock_tr.return_value,
            "coord_tr": mock_coord_tr.return_value,
            "stud": mock_stud.return_value,
            "adv": mock_adv.return_value,
            "fb": mock_fb.return_value,
        }

async def test_request_service_visibility_for_successor(mock_repos):
    service = RequestService()
    
    mock_repos["adv"].list_all.return_value = [{"uid": "adv", "id": "advisor-adv"}]
    mock_repos["stud"].list_all.return_value = []
    
    mock_repos["coord_tr"].query.return_value = [
        {
            "id": "ct1",
            "initiator_uid": "coord",
            "successor_uid": "adv",
            "status": "pendente",
            "created_at": datetime.now(timezone.utc)
        }
    ]
    
    mock_repos["fb"].list_all.return_value = [
        {"uid": "coord", "nome": "O Coordenador"}
    ]
    
    requests = await service.get_requests(_advisor())
    
    assert len(requests) == 1
    assert requests[0].tipo == "transferencia_coordenacao"
    assert requests[0].solicitante_nome == "O Coordenador"
    assert requests[0].status == "pendente"
    assert requests[0].payload_original["id"] == "ct1"

async def test_request_service_visibility_for_initiator(mock_repos):
    service = RequestService()
    
    mock_repos["stud"].list_all.return_value = []
    mock_repos["adv"].list_all.return_value = [{"uid": "coord", "id": "advisor-coord"}]
    
    async def mock_query(filters=None):
        if filters and filters[0][0] == "initiator_uid" and filters[0][2] == "coord":
            return [
                {
                    "id": "ct2",
                    "initiator_uid": "coord",
                    "successor_uid": "adv",
                    "status": "concluido",
                    "created_at": datetime.now(timezone.utc)
                }
            ]
        return []

    mock_repos["coord_tr"].query.side_effect = mock_query
    
    mock_repos["fb"].list_all.return_value = [
        {"uid": "coord", "nome": "O Ex-Coordenador"}
    ]
    
    user_ex_coord = CurrentUser(uid="coord", role="orientador", programa_id="prog1", email="c@x.com")
    requests = await service.get_requests(user_ex_coord)
    
    assert len(requests) == 1
    assert requests[0].tipo == "transferencia_coordenacao"
    assert requests[0].solicitante_nome == "O Ex-Coordenador"
    assert requests[0].status == "concluido"
    assert requests[0].payload_original["id"] == "ct2"
