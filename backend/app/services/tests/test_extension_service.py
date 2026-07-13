"""
Testes unitários do ExtensionService (Spec 08 — prorrogações de prazo).

Cobre o ciclo de vida contra fakes de repositório: solicitação (aluno), parecer
(orientador) e deliberação da coordenação — deferimento e indeferimento —, além
do escopo por papel de `list_for_user` e dos gates de negócio (pendente
duplicada, limite de `max_prorrogacoes`, tenant por programa).

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
    ApproveRequest,
    ExtensionCreateRequest,
    ExtensionStatus,
    RejectRequest,
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
    tipo: str = "prazo_defesa",
) -> dict[str, Any]:
    return {
        "id": ext_id,
        "student_id": student_id,
        "requester_id": "uid-aluno",
        "programa_id": programa_id,
        "tipo": tipo,
        "motivo": MOTIVO,
        "plano_atualizado": "http://plano.test/doc.pdf",
        "parecer_orientador": None,
        "status": status,
        "nova_data": PRAZO_NOVO,
        "data_atual": PRAZO_ATUAL,
        "created_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
    }


class _FakeExtensionRepository:
    """Fake do ExtensionRepository, com os mesmos nomes de método do real."""

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
        return next((dict(e) for e in self.extensions if e["id"] == extension_id), None)

    async def create_extension(self, data: dict[str, Any]) -> str:
        self.created = data
        return "ext_new"

    async def update_extension(self, extension_id: str, data: dict[str, Any]) -> bool:
        self.updates.append((extension_id, data))
        for item in self.extensions:
            if item["id"] == extension_id:
                item.update(data)
        return True

    async def has_pending(self, student_id: str) -> bool:
        return self.pending

    async def count_approved(self, student_id: str) -> int:
        return self.approved_count


class _FakeStudentRepository:
    def __init__(self) -> None:
        self.updates: list[tuple[str, dict[str, Any]]] = []

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

    async def get(self, student_id: str) -> dict[str, Any] | None:
        return next(
            (dict(s) for s in await self.list_all() if s["id"] == student_id),
            None,
        )

    async def get_by_uid(self, uid: str) -> dict[str, Any] | None:
        return next(
            (dict(s) for s in await self.list_all() if s["uid"] == uid),
            None,
        )

    async def update(self, student_id: str, data: dict[str, Any]) -> bool:
        self.updates.append((student_id, data))
        return True


class _FakeAdvisorRepository:
    async def query(
        self, filters: list[tuple[str, str, Any]], limit: int = 1
    ) -> list[dict[str, Any]]:
        advisors = [{"id": "advisor1", "uid": "uid-orientador", "programa_id": "prog"}]
        for campo, _, valor in filters:
            advisors = [a for a in advisors if a.get(campo) == valor]
        return advisors[:limit]


class _FakeProgramRepository:
    """Fonte canônica de `max_prorrogacoes` (Spec 08 — configuração do programa)."""

    def __init__(self, max_prorrogacoes: int = 1) -> None:
        self.max_prorrogacoes = max_prorrogacoes

    async def get_config(self, programa_id: str) -> dict[str, Any] | None:
        return {"max_prorrogacoes": self.max_prorrogacoes}


def _user(role: str, uid: str, programa_id: str | None = "prog") -> CurrentUser:
    return CurrentUser(uid=uid, role=role, programa_id=programa_id, email=f"{role}@saga.test")


def _service(
    repo: _FakeExtensionRepository | None = None,
    students: _FakeStudentRepository | None = None,
    programs: _FakeProgramRepository | None = None,
) -> ExtensionService:
    return ExtensionService(
        repository=repo or _FakeExtensionRepository(),
        students=students or _FakeStudentRepository(),
        advisors=_FakeAdvisorRepository(),
        programs=programs or _FakeProgramRepository(),
    )


# ---------------------------------------------------------------------------
# create_extension — solicitação do aluno
# ---------------------------------------------------------------------------

def _create_payload(tipo: str = "prazo_defesa") -> ExtensionCreateRequest:
    return ExtensionCreateRequest(
        tipo=tipo,
        motivo=MOTIVO,
        plano_atualizado="http://plano.test/doc.pdf",
        nova_data=PRAZO_NOVO,
    )


@pytest.mark.asyncio
async def test_create_extension_resolve_uid_para_doc_id_do_aluno() -> None:
    repo = _FakeExtensionRepository(extensions=[])

    result = await _service(repo).create_extension(
        payload=_create_payload(), requester_uid="uid-aluno"
    )

    assert result.id == "ext_new"
    # `student_id` é o doc id, não o uid — confundir os dois quebra a listagem.
    assert repo.created["student_id"] == "student1"
    assert repo.created["requester_id"] == "uid-aluno"
    assert repo.created["status"] == "pendente"
    assert repo.created["data_atual"] == PRAZO_ATUAL


@pytest.mark.asyncio
async def test_create_extension_404_quando_uid_nao_e_aluno() -> None:
    with pytest.raises(HTTPException) as exc:
        await _service().create_extension(
            payload=_create_payload(), requester_uid="uid-desconhecido"
        )

    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_create_extension_409_quando_ja_ha_pendente() -> None:
    repo = _FakeExtensionRepository(extensions=[])
    repo.pending = True

    with pytest.raises(HTTPException) as exc:
        await _service(repo).create_extension(
            payload=_create_payload(), requester_uid="uid-aluno"
        )

    assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_create_extension_409_quando_limite_de_prorrogacoes_atingido() -> None:
    repo = _FakeExtensionRepository(extensions=[])
    repo.approved_count = 1

    with pytest.raises(HTTPException) as exc:
        await _service(repo, programs=_FakeProgramRepository(max_prorrogacoes=1)).create_extension(
            payload=_create_payload(), requester_uid="uid-aluno"
        )

    assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_create_extension_respeita_max_prorrogacoes_do_programa() -> None:
    """O limite vem do programa (fonte canônica), não de uma constante do service."""
    repo = _FakeExtensionRepository(extensions=[])
    repo.approved_count = 1

    result = await _service(
        repo, programs=_FakeProgramRepository(max_prorrogacoes=2)
    ).create_extension(payload=_create_payload(), requester_uid="uid-aluno")

    assert result.id == "ext_new"


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


@pytest.mark.asyncio
async def test_add_review_403_para_orientador_de_outro_aluno() -> None:
    repo = _FakeExtensionRepository(extensions=[_extension(student_id="student2")])

    with pytest.raises(HTTPException) as exc:
        await _service(repo).add_review(
            extension_id="ext1",
            payload=ReviewRequest(parecer_orientador=PARECER),
            orientador_uid="uid-orientador",
        )

    assert exc.value.status_code == 403
    assert repo.updates == []


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
# approve_extension — deferimento da coordenação
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_approve_recalcula_prazo_final_do_aluno() -> None:
    repo = _FakeExtensionRepository()
    students = _FakeStudentRepository()

    result = await _service(repo, students=students).approve_extension(
        extension_id="ext1",
        payload=ApproveRequest(),
        coordinator=_user("coordenacao", "uid-coord"),
    )

    assert result.status == ExtensionStatus.APROVADA
    assert result.prazo_novo == PRAZO_NOVO
    assert result.aprovado_por == "uid-coord"
    assert students.updates == [
        ("student1", {"prazo_final": PRAZO_NOVO, "situacao_registrada": "em_prorrogacao"})
    ]


@pytest.mark.asyncio
async def test_approve_e_idempotente_no_prazo() -> None:
    """prazo_final é absoluto (= nova_data), não incremental: reaplicar não desloca o prazo."""
    students = _FakeStudentRepository()

    await _service(students=students).approve_extension(
        extension_id="ext1",
        payload=ApproveRequest(),
        coordinator=_user("coordenacao", "uid-coord"),
    )

    assert students.updates[0][1]["prazo_final"] == PRAZO_NOVO


@pytest.mark.asyncio
async def test_approve_trancamento_nao_move_situacao_para_em_prorrogacao() -> None:
    """Spec 08: `em_prorrogacao` só vale para prorrogação de prazo, não para trancamento."""
    repo = _FakeExtensionRepository(extensions=[_extension(tipo="trancamento")])
    students = _FakeStudentRepository()

    await _service(repo, students=students).approve_extension(
        extension_id="ext1",
        payload=ApproveRequest(),
        coordinator=_user("coordenacao", "uid-coord"),
    )

    student_id, updates = students.updates[0]
    assert student_id == "student1"
    assert updates == {"prazo_final": PRAZO_NOVO}
    assert "situacao_registrada" not in updates


@pytest.mark.asyncio
async def test_approve_persiste_observacao_da_coordenacao() -> None:
    repo = _FakeExtensionRepository()

    result = await _service(repo).approve_extension(
        extension_id="ext1",
        payload=ApproveRequest(observacao="Deferido: plano revisado é viável."),
        coordinator=_user("coordenacao", "uid-coord"),
    )

    assert result.observacao_coordenacao == "Deferido: plano revisado é viável."
    assert repo.updates[0][1]["observacao_coordenacao"] == "Deferido: plano revisado é viável."


@pytest.mark.asyncio
async def test_approve_403_quando_prorrogacao_e_de_outro_programa() -> None:
    """A coordenação do programa A não delibera prorrogação do programa B."""
    repo = _FakeExtensionRepository(extensions=[_extension(programa_id="prog-b")])
    students = _FakeStudentRepository()

    with pytest.raises(HTTPException) as exc:
        await _service(repo, students=students).approve_extension(
            extension_id="ext1",
            payload=ApproveRequest(),
            coordinator=_user("coordenacao", "uid-coord", programa_id="prog-a"),
        )

    assert exc.value.status_code == 403
    # O prazo do aluno alheio não pode ter sido reescrito.
    assert students.updates == []
    assert repo.updates == []


@pytest.mark.asyncio
async def test_approve_adm_sem_programa_delibera_qualquer_programa() -> None:
    """`programa_id` nulo é o adm global (ADR-0001) — não é bloqueado pelo tenant."""
    repo = _FakeExtensionRepository(extensions=[_extension(programa_id="prog-b")])

    result = await _service(repo).approve_extension(
        extension_id="ext1",
        payload=ApproveRequest(),
        coordinator=_user("adm", "uid-adm", programa_id=None),
    )

    assert result.status == ExtensionStatus.APROVADA


@pytest.mark.asyncio
async def test_approve_400_quando_nao_esta_pendente() -> None:
    repo = _FakeExtensionRepository(extensions=[_extension(status="rejeitada")])

    with pytest.raises(HTTPException) as exc:
        await _service(repo).approve_extension(
            extension_id="ext1",
            payload=ApproveRequest(),
            coordinator=_user("coordenacao", "uid-coord"),
        )

    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_approve_404_quando_prorrogacao_inexistente() -> None:
    with pytest.raises(HTTPException) as exc:
        await _service().approve_extension(
            extension_id="inexistente",
            payload=ApproveRequest(),
            coordinator=_user("coordenacao", "uid-coord"),
        )

    assert exc.value.status_code == 404


# ---------------------------------------------------------------------------
# reject_extension — indeferimento da coordenação
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_reject_marca_rejeitada_sem_alterar_prazo() -> None:
    repo = _FakeExtensionRepository()
    students = _FakeStudentRepository()

    result = await _service(repo, students=students).reject_extension(
        extension_id="ext1",
        payload=RejectRequest(motivo="Justificativa insuficiente."),
        coordinator=_user("coordenacao", "uid-coord"),
    )

    assert result.status == ExtensionStatus.REJEITADA
    # Spec 08: o indeferimento não toca prazo_final nem situacao_registrada.
    assert students.updates == []


@pytest.mark.asyncio
async def test_reject_persiste_motivo_e_autoria() -> None:
    """O motivo é o único registro do porquê do indeferimento — tem de ser gravado."""
    repo = _FakeExtensionRepository()

    result = await _service(repo).reject_extension(
        extension_id="ext1",
        payload=RejectRequest(motivo="Justificativa insuficiente."),
        coordinator=_user("coordenacao", "uid-coord"),
    )

    assert result.motivo_rejeicao == "Justificativa insuficiente."
    assert result.rejeitado_por == "uid-coord"
    assert result.rejeitado_em is not None

    _, updates = repo.updates[0]
    assert updates["motivo_rejeicao"] == "Justificativa insuficiente."
    assert updates["rejeitado_por"] == "uid-coord"


def test_reject_request_exige_motivo() -> None:
    """Motivo vazio é barrado no modelo (422), antes de chegar ao service."""
    with pytest.raises(ValidationError):
        RejectRequest(motivo="")


@pytest.mark.asyncio
async def test_reject_403_quando_prorrogacao_e_de_outro_programa() -> None:
    repo = _FakeExtensionRepository(extensions=[_extension(programa_id="prog-b")])

    with pytest.raises(HTTPException) as exc:
        await _service(repo).reject_extension(
            extension_id="ext1",
            payload=RejectRequest(motivo="Nao cabe."),
            coordinator=_user("coordenacao", "uid-coord", programa_id="prog-a"),
        )

    assert exc.value.status_code == 403
    assert repo.updates == []


@pytest.mark.asyncio
async def test_reject_400_quando_nao_esta_pendente() -> None:
    repo = _FakeExtensionRepository(extensions=[_extension(status="aprovada")])

    with pytest.raises(HTTPException) as exc:
        await _service(repo).reject_extension(
            extension_id="ext1",
            payload=RejectRequest(motivo="Nao cabe."),
            coordinator=_user("coordenacao", "uid-coord"),
        )

    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_reject_404_quando_prorrogacao_inexistente() -> None:
    with pytest.raises(HTTPException) as exc:
        await _service().reject_extension(
            extension_id="inexistente",
            payload=RejectRequest(motivo="Nao cabe."),
            coordinator=_user("coordenacao", "uid-coord"),
        )

    assert exc.value.status_code == 404


# ---------------------------------------------------------------------------
# list_for_user — escopo por papel
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_for_user_aluno_ve_apenas_as_proprias() -> None:
    repo = _FakeExtensionRepository(
        extensions=[_extension(), _extension(ext_id="ext2", student_id="student2")]
    )

    result = await _service(repo).list_for_user(_user("aluno", "uid-aluno"))

    assert [e.id for e in result] == ["ext1"]


@pytest.mark.asyncio
async def test_list_for_user_aluno_sem_cadastro_recebe_lista_vazia() -> None:
    result = await _service().list_for_user(_user("aluno", "uid-sem-cadastro"))

    assert result == []


@pytest.mark.asyncio
async def test_list_for_user_orientador_ve_apenas_orientandos() -> None:
    repo = _FakeExtensionRepository(
        extensions=[_extension(), _extension(ext_id="ext2", student_id="student2")]
    )

    result = await _service(repo).list_for_user(_user("orientador", "uid-orientador"))

    # advisor1 orienta apenas student1.
    assert [e.id for e in result] == ["ext1"]


@pytest.mark.asyncio
async def test_list_for_user_orientador_sem_orientandos_recebe_lista_vazia() -> None:
    result = await _service().list_for_user(_user("orientador", "uid-sem-orientandos"))

    assert result == []


@pytest.mark.asyncio
async def test_list_for_user_coordenacao_ve_apenas_o_proprio_programa() -> None:
    repo = _FakeExtensionRepository(
        extensions=[_extension(), _extension(ext_id="ext2", programa_id="prog-outro")]
    )

    result = await _service(repo).list_for_user(_user("coordenacao", "uid-coord"))

    assert [e.id for e in result] == ["ext1"]


@pytest.mark.asyncio
async def test_list_for_user_enriquece_com_dados_do_aluno() -> None:
    result = await _service().list_for_user(_user("coordenacao", "uid-coord"))

    assert result[0].student_nome == "Aluno Um"
    assert result[0].matricula == "2026001"
    assert result[0].nivel == "mestrado"


# ---------------------------------------------------------------------------
# ExtensionCreateRequest — validação de entrada
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "tipo", ["prazo_defesa", "prazo_qualificacao", "trancamento", "mudanca_nivel"]
)
def test_create_request_aceita_tipos_validos(tipo: str) -> None:
    assert _create_payload(tipo).tipo.value == tipo


def test_create_request_rejeita_tipo_invalido() -> None:
    with pytest.raises(ValidationError):
        _create_payload("tipo_inexistente")


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
        ExtensionCreateRequest(
            tipo="prazo_defesa",
            motivo=MOTIVO,
            nova_data=PRAZO_NOVO,
        )
