import pytest
from unittest.mock import AsyncMock, patch

from backend.app.core.auth import CurrentUser
from backend.app.services.request_service import RequestService


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

        service._activities = mock_act.return_value
        service._extensions = mock_ext.return_value
        service._transfers = mock_trans.return_value
        service._coord_transfers = mock_coord.return_value
        service._students = mock_stu.return_value
        service._advisors = mock_adv.return_value
        service._users = mock_fb.return_value

        yield service


@pytest.mark.asyncio
async def test_get_requests_aluno_agrega_itens_do_proprio_aluno(request_service):
    user = CurrentUser(uid="uid_aluno", email="aluno@test.com", role="aluno")

    request_service._students.query = AsyncMock(return_value=[
        {"id": "stu_1", "uid": "uid_aluno", "nome": "Aluno 1"},
    ])
    request_service._activities.list_by_student = AsyncMock(return_value=[
        {"id": "act_1", "status": "enviado", "parecer_orientador": None},
        {"id": "prod_1", "status": "enviado", "parecer_orientador": "Ok", "producao_id": "p1"},
        {"id": "draft_1", "status": "rascunho"},
    ])
    request_service._extensions.list_by_student_ids = AsyncMock(return_value=[
        {"id": "ext_1", "status": "pendente", "student_id": "stu_1", "tipo": "trancamento"},
        {"id": "ext_2", "status": "aprovada", "student_id": "stu_1", "tipo": "prorrogacao"},
        {"id": "ext_3", "status": "pendente", "student_id": "stu_1", "tipo": "prazo_defesa"},
        {"id": "ext_4", "status": "pendente", "student_id": "stu_1", "tipo": "prazo_qualificacao"},
    ])

    requests = await request_service.get_requests(user)

    # issue #298: prazo_defesa/prazo_qualificacao não colapsam mais em "prorrogacao".
    assert len(requests) == 5
    tipos = {r.tipo for r in requests}
    assert {"atividade", "producao", "trancamento", "prazo_defesa", "prazo_qualificacao"} <= tipos
    request_service._students.query.assert_called_once_with(
        filters=[("uid", "==", "uid_aluno")]
    )
    request_service._activities.list_by_student.assert_called_once_with("stu_1")
    request_service._extensions.list_by_student_ids.assert_called_once_with({"stu_1"})


@pytest.mark.asyncio
async def test_get_requests_orientador(request_service):
    user = CurrentUser(uid="uid_orientador", email="adv@test.com", role="orientador")

    request_service._advisors.query = AsyncMock(return_value=[
        {"uid": "uid_orientador", "id": "adv_1"}
    ])
    request_service._students.query = AsyncMock(return_value=[
        {"id": "stu_1", "orientador_id": "adv_1", "nome": "Aluno 1"}
    ])
    request_service._users.get = AsyncMock(return_value={"nome": "Coordenador"})

    request_service._activities.list_all_grouped = AsyncMock(return_value=[
        {"id": "act_1", "status": "enviado", "parecer_orientador": None, "student_id": "stu_1"},
        {"id": "prod_1", "status": "enviado", "parecer_orientador": None, "producao_id": "p1", "student_id": "stu_1"},
        # Atividade de aluno de outro orientador não deve aparecer.
        {"id": "act_2", "status": "enviado", "parecer_orientador": None, "student_id": "stu_outro"},
    ])

    request_service._extensions.list_by_student_ids = AsyncMock(return_value=[
        {
            "id": "ext_1",
            "status": "pendente",
            "student_id": "stu_1",
            "parecer_orientador": None,
            "parecer": None,
        }
    ])

    # Duas consultas: como sucessor (1 convite pendente) e como iniciador (nenhum).
    request_service._coord_transfers.query = AsyncMock(side_effect=[
        [{"id": "ct_1", "status": "pendente", "initiator_uid": "uid_coord"}],
        [],
    ])

    requests = await request_service.get_requests(user)

    assert len(requests) == 4
    tipos = {r.tipo for r in requests}
    assert "atividade" in tipos
    assert "producao" in tipos
    assert "prorrogacao" in tipos
    assert "transferencia_coordenacao" in tipos


@pytest.mark.asyncio
async def test_get_requests_origem_por_tipo(request_service):
    """Cada RequestItem carrega a origem correta (Solicitacao, CONTEXT.md):

    - formulario: prorrogacao (inclui prazo_defesa/prazo_qualificacao, issue #298),
      trancamento, transferencia (de orientando)
    - agregado: atividade (inclui producao), transferencia_coordenacao
    """
    user = CurrentUser(uid="uid_coord", email="coord@test.com", role="coordenacao", programa_id="prog_1")

    request_service._students.list_all = AsyncMock(return_value=[
        {"id": "stu_1", "programa_id": "prog_1", "nome": "Aluno 1"}
    ])
    request_service._advisors.get = AsyncMock(return_value={"nome": "Orientador"})
    request_service._users.list_all = AsyncMock(return_value=[])
    request_service._users.get = AsyncMock(return_value={"nome": "Sucessor"})

    request_service._activities.list_all_grouped = AsyncMock(return_value=[
        {"id": "act_1", "status": "enviado", "parecer_orientador": "Aprovado", "student_id": "stu_1"}
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
    assert origem_by_tipo["prazo_defesa"] == "formulario"
    assert origem_by_tipo["trancamento"] == "formulario"
    assert origem_by_tipo["transferencia"] == "formulario"
    assert origem_by_tipo["transferencia_coordenacao"] == "agregado"


@pytest.mark.asyncio
async def test_get_requests_coordenacao(request_service):
    user = CurrentUser(
        uid="uid_coord",
        email="coord@test.com",
        role="coordenacao",
        programa_id="prog_1",
    )

    request_service._students.list_all = AsyncMock(return_value=[
        {"id": "stu_2", "programa_id": "prog_1", "nome": "Aluno Prog 1"}
    ])
    request_service._advisors.get = AsyncMock(return_value={"nome": "Orientador"})
    request_service._users.get = AsyncMock(return_value=None)

    request_service._activities.list_all_grouped = AsyncMock(return_value=[
        {
            "id": "act_2",
            "status": "enviado",
            "parecer_orientador": "Aprovado",
            "producao_id": "p2",
            "student_id": "stu_2",
        }
    ])

    request_service._extensions.list_all = AsyncMock(return_value=[
        {
            "id": "ext_2",
            "status": "pendente",
            "student_id": "stu_2",
            "parecer_orientador": "Ok",
            "tipo": "trancamento",
        }
    ])

    request_service._transfers.list_by_program = AsyncMock(return_value=[
        {
            "id": "tr_1",
            "status": "pendente",
            "student_id": "stu_2",
            "solicitante_id": "adv_x",
        }
    ])

    request_service._coord_transfers.list_by_program = AsyncMock(return_value=[
        {
            "id": "ct_2",
            "status": "pendente",
            "initiator_uid": "uid_coord",
            "successor_uid": "uid_outro",
        }
    ])

    requests = await request_service.get_requests(user)

    assert len(requests) == 4
    tipos = {r.tipo for r in requests}
    assert "producao" in tipos
    assert "trancamento" in tipos
    assert "transferencia" in tipos
    assert "transferencia_coordenacao" in tipos


@pytest.mark.asyncio
async def test_get_requests_adm(request_service):
    user = CurrentUser(uid="uid_adm", email="adm@test.com", role="adm")

    request_service._coord_transfers.list_all = AsyncMock(return_value=[
        {"id": "ct_3", "status": "pendente", "initiator_uid": "uid_coord"}
    ])
    request_service._users.get = AsyncMock(return_value=None)

    requests = await request_service.get_requests(user)

    assert len(requests) == 1
    assert requests[0].tipo == "transferencia_coordenacao"


@pytest.mark.parametrize(
    "extension_tipo, expected",
    [
        ({"tipo": "trancamento"}, "trancamento"),
        ({"tipo": "prazo_defesa"}, "prazo_defesa"),
        ({"tipo": "prazo_qualificacao"}, "prazo_qualificacao"),
        ({"tipo": "prorrogacao"}, "prorrogacao"),
        ({"tipo": "mudanca_nivel"}, "prorrogacao"),
        ({}, "prorrogacao"),
    ],
)
def test_extension_request_type_preserva_subtipos(extension_tipo, expected):
    """issue #298: prazo_defesa/prazo_qualificacao não colapsam mais em 'prorrogacao'."""
    assert RequestService._extension_request_type(extension_tipo) == expected
