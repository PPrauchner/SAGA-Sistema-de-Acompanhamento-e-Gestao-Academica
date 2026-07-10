"""
Testes unitários do ExtensionService (Spec 08 — prorrogações de prazo).

Cobre os três casos de uso do ciclo de vida contra fakes de repositório:
solicitação (aluno), parecer (orientador) e decisão (coordenação), além do
escopo por papel de `list_for_user` e dos gates de negócio (pendente duplicada,
limite de `max_prorrogacoes`).

Identidade: os fakes distinguem uid do Firebase Auth (campo `uid`) do doc id
(campo `id`), como a coleção real — é onde os bugs de resolução aparecem.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from backend.app.core.auth import CurrentUser
from backend.app.models.extension import (
    DecisionRequest,
    ExtensionCreateRequest,
    ExtensionStatus,
    ReviewRequest,
)
from backend.app.services.extension_service import ExtensionService

PRAZO_ATUAL = datetime(2028, 1, 1, tzinfo=timezone.utc)
PRAZO_NOVO = datetime(2028, 7, 1, tzinfo=timezone.utc)
MOTIVO = "Motivo longo o suficiente para passar na validacao"
PARECER = "Parecer tecnico favoravel do orientador"


def _extension(
    ext_id: str = "ext1",
    student_id: str = "student1",
    status: str = "pendente",
    programa_id: str = "prog",
) -> dict[str, Any]:
    return {
        "id": ext_id,
        "student_id": student_id,
        "requester_id": "uid-aluno",
        "programa_id": programa_id,
        "tipo": "prazo_defesa",
        "motivo": MOTIVO,
        "plano_atualizado": "http://plano.test/doc.pdf",
        "parecer_orientador": None,
        "status": status,
        "nova_data": PRAZO_NOVO,
        "data_atual": PRAZO_ATUAL,
        "created_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
    }


class _FakeExtensionRepository:
    def __init__(self, extensions: list[dict[str, Any]] | None = None) -> None:
        self.extensions = extensions if extensions is not None else [_extension()]
        self.created: dict[str, Any] | None = None
        self.updates: list[tuple[str, dict[str, Any]]] = []
        self.pending = False
        self.approved_count = 0

    async def list_all(self) -> list[dict[str, Any]]:
        return list(self.extensions)

    async def list_by_student(self, student_id: str) -> list[dict[str, Any]]:
        return [e for e in self.extensions if e["student_id"] == student_id]

    async def get_extension(self, extension_id: str) -> dict[str, Any] | None:
        return next((e for e in self.extensions if e["id"] == extension_id), None)

    async def create_extension(self, data: dict[str, Any]) -> str:
        self.created = data
        return "ext_new"

    async def get(self, extension_id: str) -> dict[str, Any] | None:
        return next(
            (dict(item) for item in self.extensions if item["id"] == extension_id),
            None,
        )

    async def update(self, extension_id: str, data: dict[str, Any]) -> bool:
        for item in self.extensions:
            if item["id"] == extension_id:
                item.update(data)
        return True


class _PendingExtensionRepository(_FakeExtensionRepository):
    async def has_pending_for_student(self, student_id: str) -> bool:
        return True

    async def has_pending(self, student_id: str) -> bool:
        return self.pending

    async def count_approved(self, student_id: str) -> int:
        return self.approved_count


class _FakeStudentRepository:
    def __init__(self) -> None:
        self.updates: dict[str, dict[str, Any]] = {}

    async def list_all(self) -> list[dict[str, Any]]:
        return [
            {
                "id": "student1",
                "uid": "uid-aluno",
                "nome": "Aluno Um",
                "matricula": "2026001",
                "nivel": "mestrado",
                "orientador_id": "advisor1",
                "programa_id": "prog",
                "prazo_final": PRAZO_ATUAL,
            },
            {
                "id": "student2",
                "uid": "uid-outro",
                "nome": "Aluno Dois",
                "matricula": "2026002",
                "nivel": "doutorado",
                "orientador_id": "advisor2",
                "programa_id": "prog",
                "prazo_final": PRAZO_ATUAL,
            },
        ]

    async def list_by_program(self, programa_id: str) -> list[dict[str, Any]]:
        return [
            student
            for student in await self.list_all()
            if student.get("programa_id") == programa_id
        ]

    async def get(self, student_id: str) -> dict[str, Any] | None:
        return next(
            (dict(student) for student in await self.list_all() if student["id"] == student_id),
            None,
        )

    async def update(self, student_id: str, data: dict[str, Any]) -> bool:
        self.updates[student_id] = {**self.updates.get(student_id, {}), **data}
        return True


class _MixedExtensionRepository(_FakeExtensionRepository):
    """Inclui uma prorrogação aprovada e uma de outro programa, para testar o filtro."""

    def __init__(self) -> None:
        super().__init__()
        self.extensions = self.extensions + [
            {
                "id": "ext3",
                "student_id": "student1",
                "tipo": "prazo_defesa",
                "status": "aprovada",
                "motivo": "Aprovada",
                "nova_data": date(2028, 9, 1),
                "programa_id": "prog",
            },
            {
                "id": "ext4",
                "student_id": "studentX",
                "tipo": "prazo_defesa",
                "status": "pendente",
                "motivo": "Outro programa",
                "nova_data": date(2028, 9, 1),
                "programa_id": "prog_outro",
            },
        ]


class _TrancamentoSemDataRepository(_FakeExtensionRepository):
    """Trancamento pendente sem `nova_data` (permitido pelo modelo)."""

    def __init__(self) -> None:
        super().__init__()
        self.extensions = [
            {
                "id": "ext_tranc",
                "student_id": "student1",
                "tipo": "trancamento",
                "status": "pendente",
                "motivo": "Licenca medica",
                "nova_data": None,
                "programa_id": "prog",
            }
        ]


class _FakeAdvisorRepository:
    async def list_all(self) -> list[dict[str, Any]]:
        return [
            {"id": "advisor1", "uid": "uid-orientador", "programa_id": "prog"},
        ]


def _user(role: str, uid: str, programa_id: str | None = "prog") -> CurrentUser:
    return CurrentUser(uid=uid, role=role, programa_id=programa_id, email=f"{role}@saga.test")


def _service(
    repo: _FakeExtensionRepository | None = None,
    students: _FakeStudentRepository | None = None,
    programs: _FakeProgramRepository | None = None,
) -> ExtensionService:
    return ExtensionService(
        repo=repo or _FakeExtensionRepository(),
        student_repo=_FakeStudentRepository(),
        advisor_repo=_FakeAdvisorRepository(),
    )


def _service_with(
    repo: _FakeExtensionRepository,
    student_repo: _FakeStudentRepository,
) -> ExtensionService:
    return ExtensionService(
        repo=repo,
        student_repo=student_repo,
        advisor_repo=_FakeAdvisorRepository(),
    )


@pytest.mark.asyncio
async def test_create_extension_resolve_uid_para_doc_id_do_aluno() -> None:
    repo = _FakeExtensionRepository(extensions=[])
    result = await _service(repo).create_extension(_create_payload(), requester_uid="uid-aluno")

    assert result.id == "ext_new"
    assert repo.created is not None
    # student_id é o doc id; requester_id é o uid do Auth. Trocá-los é o bug histórico.
    assert repo.created["student_id"] == "student1"
    assert repo.created["requester_id"] == "uid-aluno"
    assert repo.created["programa_id"] == "prog"
    assert repo.created["data_atual"] == PRAZO_ATUAL


@pytest.mark.asyncio
async def test_create_extension_404_quando_uid_nao_e_aluno() -> None:
    with pytest.raises(HTTPException) as exc:
        await _service().create_extension(_create_payload(), requester_uid="uid-desconhecido")

    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_create_extension_409_quando_ja_ha_pendente() -> None:
    repo = _FakeExtensionRepository()
    repo.pending = True

    with pytest.raises(HTTPException) as exc:
        await _service(repo).create_extension(_create_payload(), requester_uid="uid-aluno")

    assert exc.value.status_code == 409
    assert "pendente" in exc.value.detail.lower()


@pytest.mark.asyncio
async def test_create_extension_409_quando_limite_de_prorrogacoes_atingido() -> None:
    repo = _FakeExtensionRepository(extensions=[])
    repo.approved_count = 1

    with pytest.raises(HTTPException) as exc:
        await _service(repo, programs=_FakeProgramRepository(max_prorrogacoes=1)).create_extension(
            _create_payload(), requester_uid="uid-aluno"
        )

    assert exc.value.status_code == 409
    assert "limite" in exc.value.detail.lower()


@pytest.mark.asyncio
async def test_create_extension_respeita_max_prorrogacoes_do_programa() -> None:
    """max_prorrogacoes vem do programa (fonte canônica), não de uma constante."""
    repo = _FakeExtensionRepository(extensions=[])
    repo.approved_count = 1

    result = await _service(repo, programs=_FakeProgramRepository(max_prorrogacoes=2)).create_extension(
        _create_payload(), requester_uid="uid-aluno"
    )

    assert result.status == ExtensionStatus.PENDENTE


# ---------------------------------------------------------------------------
# add_review — parecer do orientador
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_add_review_registra_parecer_do_orientador_do_aluno() -> None:
    repo = _FakeExtensionRepository()
    result = await _service(repo).add_review(
        extension_id="ext1",
        payload=ReviewRequest(parecer_orientador=PARECER),
        orientador_uid="uid-orientador",
    )

    assert result.parecer_orientador == PARECER
    assert repo.updates == [("ext1", {"parecer_orientador": PARECER})]
    # Parecer é campo, não estado: o status continua pendente.
    assert result.status == ExtensionStatus.PENDENTE


@pytest.mark.asyncio
async def test_add_review_403_para_orientador_de_outro_aluno() -> None:
    with pytest.raises(HTTPException) as exc:
        await _service().add_review(
            extension_id="ext1",
            payload=ReviewRequest(parecer_orientador=PARECER),
            orientador_uid="uid-outro-orientador",
        )

    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_add_review_404_quando_prorrogacao_inexistente() -> None:
    with pytest.raises(HTTPException) as exc:
        await _service().add_review(
            extension_id="inexistente",
            payload=ReviewRequest(parecer_orientador=PARECER),
            orientador_uid="uid-orientador",
        )

    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_add_review_400_quando_nao_esta_pendente() -> None:
    repo = _FakeExtensionRepository(extensions=[_extension(status="aprovada")])

    with pytest.raises(HTTPException) as exc:
        await _service(repo).add_review(
            extension_id="ext1",
            payload=ReviewRequest(parecer_orientador=PARECER),
            orientador_uid="uid-orientador",
        )

    assert exc.value.status_code == 400


# ---------------------------------------------------------------------------
# process_decision — homologação da coordenação
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_process_decision_aprovar_recalcula_prazo_final_do_aluno() -> None:
    repo = _FakeExtensionRepository()
    students = _FakeStudentRepository()

    result = await _service(repo, students=students).process_decision(
        extension_id="ext1",
        payload=DecisionRequest(acao="aprovar"),
        coordinator=_user("coordenacao", "uid-coord"),
    )

    assert result.status == ExtensionStatus.APROVADA
    assert result.prazo_novo == PRAZO_NOVO
    assert result.aprovado_por == "uid-coord"
    assert students.updates == [
        ("student1", {"prazo_final": PRAZO_NOVO, "situacao_registrada": "em_prorrogacao"})
    ]


@pytest.mark.asyncio
async def test_process_decision_aprovar_e_idempotente_no_prazo() -> None:
    """prazo_final é absoluto (= nova_data), não incremental: reaplicar não desloca o prazo."""
    students = _FakeStudentRepository()
    await _service(students=students).process_decision(
        extension_id="ext1",
        payload=DecisionRequest(acao="aprovar"),
        coordinator=_user("coordenacao", "uid-coord"),
    )

    assert students.updates[0][1]["prazo_final"] == PRAZO_NOVO


@pytest.mark.asyncio
async def test_process_decision_rejeitar_nao_toca_no_prazo_final() -> None:
    repo = _FakeExtensionRepository()
    students = _FakeStudentRepository()

    result = await _service(repo, students=students).process_decision(
        extension_id="ext1",
        payload=DecisionRequest(acao="rejeitar"),
        coordinator=_user("coordenacao", "uid-coord"),
    )

    assert result.status == ExtensionStatus.REJEITADA
    assert students.updates == []
    assert repo.updates == [("ext1", {"status": "rejeitada", "observacao_coordenacao": None})]


@pytest.mark.asyncio
async def test_process_decision_aprovar_persiste_observacao_da_coordenacao() -> None:
    repo = _FakeExtensionRepository()

    result = await _service(repo).process_decision(
        extension_id="ext1",
        payload=DecisionRequest(acao="aprovar", observacao="Deferido: plano revisado é viável."),
        coordinator=_user("coordenacao", "uid-coord"),
    )

    assert result.observacao_coordenacao == "Deferido: plano revisado é viável."
    assert repo.updates[0][1]["observacao_coordenacao"] == "Deferido: plano revisado é viável."


@pytest.mark.asyncio
async def test_process_decision_rejeitar_persiste_observacao_da_coordenacao() -> None:
    """No indeferimento a observação é o único registro do porquê da decisão."""
    repo = _FakeExtensionRepository()

    result = await _service(repo).process_decision(
        extension_id="ext1",
        payload=DecisionRequest(acao="rejeitar", observacao="Indeferido: justificativa insuficiente."),
        coordinator=_user("coordenacao", "uid-coord"),
    )

    assert result.observacao_coordenacao == "Indeferido: justificativa insuficiente."
    assert repo.updates[0][1]["observacao_coordenacao"] == "Indeferido: justificativa insuficiente."


@pytest.mark.asyncio
async def test_process_decision_403_quando_prorrogacao_e_de_outro_programa() -> None:
    """A coordenação do programa A não delibera prorrogação do programa B."""
    repo = _FakeExtensionRepository(extensions=[_extension(programa_id="prog-b")])
    students = _FakeStudentRepository()

    with pytest.raises(HTTPException) as exc:
        await _service(repo, students=students).process_decision(
            extension_id="ext1",
            payload=DecisionRequest(acao="aprovar"),
            coordinator=_user("coordenacao", "uid-coord", programa_id="prog-a"),
        )

    assert exc.value.status_code == 403
    # O prazo do aluno alheio não pode ter sido reescrito.
    assert students.updates == []
    assert repo.updates == []


@pytest.mark.asyncio
async def test_process_decision_adm_sem_programa_delibera_qualquer_programa() -> None:
    """`programa_id` nulo é o adm global (ADR-0001) — não é bloqueado pelo tenant."""
    repo = _FakeExtensionRepository(extensions=[_extension(programa_id="prog-b")])
    students = _FakeStudentRepository()

    result = await _service(repo, students=students).process_decision(
        extension_id="ext1",
        payload=DecisionRequest(acao="aprovar"),
        coordinator=_user("adm", "uid-adm", programa_id=None),
    )

    assert result.status == ExtensionStatus.APROVADA


@pytest.mark.asyncio
async def test_process_decision_400_quando_nao_esta_pendente() -> None:
    repo = _FakeExtensionRepository(extensions=[_extension(status="rejeitada")])

    with pytest.raises(HTTPException) as exc:
        await _service(repo).process_decision(
            extension_id="ext1",
            payload=DecisionRequest(acao="aprovar"),
            coordinator=_user("coordenacao", "uid-coord"),
        )

    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_process_decision_404_quando_prorrogacao_inexistente() -> None:
    with pytest.raises(HTTPException) as exc:
        await _service().process_decision(
            extension_id="inexistente",
            payload=DecisionRequest(acao="aprovar"),
            coordinator=_user("coordenacao", "uid-coord"),
        )

    assert exc.value.status_code == 404


# ---------------------------------------------------------------------------
# list_for_user — escopo por papel
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_for_user_aluno_ve_apenas_as_proprias() -> None:
    repo = _FakeExtensionRepository(
        extensions=[_extension("ext1", "student1"), _extension("ext2", "student2")]
    )

    result = await _service(repo).list_for_user(_user("aluno", "uid-aluno"))

    assert [e.id for e in result] == ["ext1"]
    assert result[0].student_nome == "Aluno Um"


@pytest.mark.asyncio
async def test_list_for_user_aluno_sem_cadastro_recebe_lista_vazia() -> None:
    result = await _service().list_for_user(_user("aluno", "uid-sem-cadastro"))

    assert result == []


@pytest.mark.asyncio
async def test_list_for_user_orientador_ve_apenas_orientandos() -> None:
    repo = _FakeExtensionRepository(
        extensions=[_extension("ext1", "student1"), _extension("ext2", "student2")]
    )

    result = await _service(repo).list_for_user(_user("orientador", "uid-orientador"))

    # advisor1 orienta student1; student2 é de advisor2.
    assert [e.id for e in result] == ["ext1"]


@pytest.mark.asyncio
async def test_list_for_user_orientador_sem_orientandos_recebe_lista_vazia() -> None:
    result = await _service().list_for_user(_user("orientador", "uid-nao-orientador"))

    assert result == []


@pytest.mark.asyncio
async def test_list_for_user_coordenacao_ve_apenas_o_proprio_programa() -> None:
    repo = _FakeExtensionRepository(
        extensions=[
            _extension("ext1", "student1", programa_id="prog"),
            _extension("ext2", "student2", programa_id="prog_outro"),
        ]
    )

    result = await _service(repo).list_for_user(_user("coordenacao", "uid-coord"))

    assert [e.id for e in result] == ["ext1"]


@pytest.mark.asyncio
async def test_list_for_user_enriquece_com_dados_do_aluno() -> None:
    """A listagem carrega nome, matrícula e nível — o dashboard da coordenação os exibe."""
    repo = _FakeExtensionRepository(
        extensions=[_extension("ext1", "student1"), _extension("ext2", "student2")]
    )

    result = await _service(repo).list_for_user(_user("coordenacao", "uid-coord"))

    por_id = {e.id: e for e in result}
    assert por_id["ext1"].student_nome == "Aluno Um"
    assert por_id["ext1"].matricula == "2026001"
    assert por_id["ext1"].nivel == "mestrado"
    assert por_id["ext2"].nivel == "doutorado"


# ---------------------------------------------------------------------------
# ExtensionCreateRequest — invariantes do modelo
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "tipo", ["prazo_defesa", "prazo_qualificacao", "trancamento", "mudanca_nivel"]
)
def test_create_request_aceita_tipos_validos(tipo: str) -> None:
    request = ExtensionCreateRequest(
        tipo=tipo,
        motivo=MOTIVO,
        plano_atualizado="http://plano.test/doc.pdf",
        nova_data=PRAZO_NOVO,
    )

    assert request.tipo == tipo


def test_create_request_rejeita_tipo_invalido() -> None:
    with pytest.raises(ValidationError):
        ExtensionCreateRequest(
            tipo="qualquer",
            motivo=MOTIVO,
            plano_atualizado="http://plano.test/doc.pdf",
            nova_data=PRAZO_NOVO,
        )


def test_create_request_rejeita_motivo_curto() -> None:
    with pytest.raises(ValidationError):
        ExtensionCreateRequest(
            tipo="prazo_defesa",
            motivo="curto",
            plano_atualizado="http://plano.test/doc.pdf",
            nova_data=PRAZO_NOVO,
        )


def test_create_request_exige_plano_atualizado() -> None:
    with pytest.raises(ValidationError):
        ExtensionCreateRequest(nova_data=date(2028, 7, 1), motivo="Ajuste")


@pytest.mark.asyncio
async def test_approve_extension_recalcula_prazo_do_aluno() -> None:
    repo = _FakeExtensionRepository()
    student_repo = _FakeStudentRepository()
    service = _service_with(repo, student_repo)

    result = await service.approve_extension("ext1", _user("coordenacao", "uid-coord"))

    assert result["status"] == "aprovada"
    assert student_repo.updates["student1"]["prazo_final"] == date(2028, 7, 1)
    assert repo.extensions[0]["aprovado_por"] == "uid-coord"


@pytest.mark.asyncio
async def test_approve_prorrogacao_move_situacao_para_em_prorrogacao() -> None:
    repo = _FakeExtensionRepository()
    student_repo = _FakeStudentRepository()
    service = _service_with(repo, student_repo)

    result = await service.approve_extension("ext1", _user("coordenacao", "uid-coord"))

    # Prorrogação aprovada move o aluno para "Em Prorrogação" (CONTEXT.md → Prorrogação).
    assert student_repo.updates["student1"]["situacao_registrada"] == "em_prorrogacao"
    assert result["situacao_registrada"] == "em_prorrogacao"


@pytest.mark.asyncio
async def test_approve_trancamento_nao_muda_situacao() -> None:
    repo = _TrancamentoSemDataRepository()
    student_repo = _FakeStudentRepository()
    service = _service_with(repo, student_repo)

    result = await service.approve_extension(
        "ext_tranc", _user("coordenacao", "uid-coord")
    )

    # Trancamento não dispara a transição de "Em Prorrogação".
    assert "student1" not in student_repo.updates
    assert result["situacao_registrada"] is None


@pytest.mark.asyncio
async def test_approve_trancamento_sem_data_preserva_prazo() -> None:
    repo = _TrancamentoSemDataRepository()
    student_repo = _FakeStudentRepository()
    service = _service_with(repo, student_repo)

    result = await service.approve_extension(
        "ext_tranc", _user("coordenacao", "uid-coord")
    )

    assert result["status"] == "aprovada"
    # Sem nova_data, a aprovacao nao pode sobrescrever (zerar) o prazo_final do aluno.
    assert "student1" not in student_repo.updates


@pytest.mark.asyncio
async def test_approve_extension_bloqueia_nao_pendente() -> None:
    repo = _FakeExtensionRepository()
    repo.extensions[0]["status"] = "aprovada"
    service = _service_with(repo, _FakeStudentRepository())

    with pytest.raises(HTTPException) as exc:
        await service.approve_extension("ext1", _user("coordenacao", "uid-coord"))

    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_approve_extension_bloqueia_outro_programa() -> None:
    repo = _FakeExtensionRepository()
    service = _service_with(repo, _FakeStudentRepository())
    outro_programa = CurrentUser(
        uid="uid-coord2", role="coordenacao", programa_id="prog_outro", email="c2@saga.test"
    )

    with pytest.raises(HTTPException) as exc:
        await service.approve_extension("ext1", outro_programa)

    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_reject_extension_exige_motivo() -> None:
    repo = _FakeExtensionRepository()
    service = _service_with(repo, _FakeStudentRepository())

    with pytest.raises(HTTPException) as exc:
        await service.reject_extension("ext1", "  ", _user("coordenacao", "uid-coord"))

    assert exc.value.status_code == 422


@pytest.mark.asyncio
async def test_reject_extension_marca_rejeitada_sem_alterar_prazo() -> None:
    repo = _FakeExtensionRepository()
    student_repo = _FakeStudentRepository()
    service = _service_with(repo, student_repo)

    result = await service.reject_extension(
        "ext1", "Sem justificativa suficiente", _user("coordenacao", "uid-coord")
    )

    assert result["status"] == "rejeitada"
    assert repo.extensions[0]["motivo_rejeicao"] == "Sem justificativa suficiente"
    assert "student1" not in student_repo.updates
