import pytest
from unittest.mock import AsyncMock, patch

from backend.app.core.auth import CurrentUser
from backend.app.services.request_service import RequestService
from backend.app.models.request import RequestItem


@pytest.fixture
def request_service():
    with patch("backend.app.services.request_service.ActivityRepository") as mock_act, \
         patch("backend.app.services.request_service.ExtensionRepository") as mock_ext, \
         patch("backend.app.services.request_service.TransferRepository") as mock_trans, \
         patch("backend.app.services.request_service.CoordinationTransferRepository") as mock_coord, \
         patch("backend.app.services.request_service.StudentRepository") as mock_stu, \
         patch("backend.app.services.request_service.AdvisorRepository") as mock_adv, \
         patch("backend.app.services.request_service.FirebaseRepository") as mock_fb:
        
        service = RequestService()
        
        # Mocks para repositorios
        service._activities = mock_act.return_value
        service._extensions = mock_ext.return_value
        service._transfers = mock_trans.return_value
        service._coord_transfers = mock_coord.return_value
        service._students = mock_stu.return_value
        service._advisors = mock_adv.return_value
        service._users = mock_fb.return_value
        
        yield service


@pytest.mark.asyncio
async def test_get_requests_orientador(request_service):
    user = CurrentUser(uid="uid_orientador", email="adv@test.com", role="orientador")

    # Setup mocks
    request_service._advisors.list_all = AsyncMock(return_value=[{"uid": "uid_orientador", "id": "adv_1"}])
    request_service._students.list_all = AsyncMock(return_value=[{"id": "stu_1", "orientador_id": "adv_1", "nome": "Aluno 1"}])
    request_service._users.list_all = AsyncMock(return_value=[])

    # Atividade pendente para o orientador (sem parecer)
    request_service._activities.list_by_student = AsyncMock(return_value=[
        {"id": "act_1", "status": "enviado", "parecer_orientador": None}
    ])

    # Prorrogacao pendente
    request_service._extensions.list_by_student_ids = AsyncMock(return_value=[
        {"id": "ext_1", "status": "pendente", "student_id": "stu_1", "parecer_orientador": None, "parecer": None}
    ])

    # Transferencia de coordenacao de destino
    request_service._coord_transfers.list_pending_for_successor = AsyncMock(return_value=[
        {"id": "ct_1", "status": "pendente", "initiator_uid": "uid_coord"}
    ])

    requests = await request_service.get_requests(user)

    assert len(requests) == 3
    tipos = {r.tipo for r in requests}
    assert "atividade" in tipos
    assert "prorrogacao" in tipos
    assert "transferencia_coordenacao" in tipos


@pytest.mark.asyncio
async def test_get_requests_origem_por_tipo(request_service):
    """Cada RequestItem carrega a origem correta (Solicitacao, CONTEXT.md):

    - formulario: prorrogacao, trancamento, transferencia (de orientando)
    - agregado: atividade (inclui producao), transferencia_coordenacao
    """
    user = CurrentUser(uid="uid_coord", email="coord@test.com", role="coordenacao", programa_id="prog_1")

    request_service._students.list_all = AsyncMock(return_value=[
        {"id": "stu_1", "programa_id": "prog_1", "nome": "Aluno 1"}
    ])
    request_service._advisors.get = AsyncMock(return_value={"nome": "Orientador"})
    request_service._users.list_all = AsyncMock(return_value=[])

    request_service._activities.list_by_student = AsyncMock(return_value=[
        {"id": "act_1", "status": "enviado", "parecer_orientador": "Aprovado"}
    ])
    # Uma prorrogacao de prazo e um trancamento, ambos aguardando a coordenacao.
    request_service._extensions.list_all = AsyncMock(return_value=[
        {"id": "ext_1", "tipo": "prazo_defesa", "status": "pendente", "student_id": "stu_1", "parecer_orientador": "Ok"},
        {"id": "ext_2", "tipo": "trancamento", "status": "pendente", "student_id": "stu_1", "parecer_orientador": "Ok"},
    ])
    request_service._transfers.list_by_program = AsyncMock(return_value=[
        {"id": "tr_1", "status": "pendente", "student_id": "stu_1", "solicitante_id": "adv_x"}
    ])
    request_service._coord_transfers.list_by_program = AsyncMock(return_value=[
        {"id": "ct_1", "status": "pendente", "initiator_uid": "uid_coord", "successor_uid": "uid_outro"}
    ])

    requests = await request_service.get_requests(user)
    origem_by_tipo = {r.tipo: r.origem for r in requests}

    assert origem_by_tipo["atividade"] == "agregado"
    assert origem_by_tipo["prorrogacao"] == "formulario"
    assert origem_by_tipo["trancamento"] == "formulario"
    assert origem_by_tipo["transferencia"] == "formulario"
    assert origem_by_tipo["transferencia_coordenacao"] == "agregado"


@pytest.mark.asyncio
async def test_get_requests_coordenacao(request_service):
    user = CurrentUser(uid="uid_coord", email="coord@test.com", role="coordenacao", programa_id="prog_1")
    
    request_service._students.list_all = AsyncMock(return_value=[{"id": "stu_2", "programa_id": "prog_1", "nome": "Aluno Prog 1"}])
    request_service._advisors.get = AsyncMock(return_value={"nome": "Orientador"})
    request_service._users.list_all = AsyncMock(return_value=[])
    
    # Atividade aguardando coordenacao (com parecer)
    request_service._activities.list_by_student = AsyncMock(return_value=[
        {"id": "act_2", "status": "enviado", "parecer_orientador": "Aprovado"}
    ])
    
    # Prorrogacao com parecer
    request_service._extensions.list_all = AsyncMock(return_value=[
        {"id": "ext_2", "status": "pendente", "student_id": "stu_2", "parecer_orientador": "Ok"}
    ])
    
    # Transferencia de orientando no programa
    request_service._transfers.list_by_program = AsyncMock(return_value=[
        {"id": "tr_1", "status": "pendente", "student_id": "stu_2", "solicitante_id": "adv_x"}
    ])
    
    # Transferencia de coordenacao criada por este usuario (acompanhamento)
    request_service._coord_transfers.list_by_program = AsyncMock(return_value=[
        {"id": "ct_2", "status": "pendente", "initiator_uid": "uid_coord", "successor_uid": "uid_outro"}
    ])
    
    requests = await request_service.get_requests(user)
    
    assert len(requests) == 4


@pytest.mark.asyncio
async def test_get_requests_adm(request_service):
    user = CurrentUser(uid="uid_adm", email="adm@test.com", role="adm")
    
    request_service._coord_transfers.list_all = AsyncMock(return_value=[
        {"id": "ct_3", "status": "pendente", "initiator_uid": "uid_coord"}
    ])
    request_service._users.list_all = AsyncMock(return_value=[])
    
    requests = await request_service.get_requests(user)
    
    assert len(requests) == 1
    assert requests[0].tipo == "transferencia_coordenacao"
