from __future__ import annotations

from datetime import date
from typing import Any

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from backend.app.core.auth import CurrentUser
from backend.app.models.extension import ExtensionCreateRequest
from backend.app.services.extension_service import ExtensionService


class _FakeExtensionRepository:
    def __init__(self) -> None:
        self.created: dict[str, Any] | None = None
        self.extensions = [
            {
                "id": "ext1",
                "student_id": "student1",
                "tipo": "prazo_defesa",
                "status": "pendente",
                "motivo": "Ajuste",
                "nova_data": date(2028, 7, 1),
                "programa_id": "prog",
            },
            {
                "id": "ext2",
                "student_id": "student2",
                "tipo": "prazo_defesa",
                "status": "pendente",
                "motivo": "Outro",
                "nova_data": date(2028, 8, 1),
                "programa_id": "prog",
            },
        ]

    async def list_all(self) -> list[dict[str, Any]]:
        return self.extensions

    async def list_by_program(
        self, programa_id: str, status: str | None = None
    ) -> list[dict[str, Any]]:
        return [
            item
            for item in self.extensions
            if item.get("programa_id") == programa_id
            and (status is None or item.get("status") == status)
        ]

    async def list_by_student_ids(self, student_ids: set[str]) -> list[dict[str, Any]]:
        return [
            item
            for item in self.extensions
            if item["student_id"] in student_ids
        ]

    async def has_pending_for_student(self, student_id: str) -> bool:
        return False

    async def create(self, data: dict[str, Any]) -> str:
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
            },
            {
                "id": "student2",
                "uid": "uid-outro",
                "nome": "Aluno Dois",
                "matricula": "2026002",
                "nivel": "doutorado",
                "orientador_id": "advisor2",
                "programa_id": "prog",
            },
        ]

    async def list_by_program(self, programa_id: str) -> list[dict[str, Any]]:
        return [
            student
            for student in await self.list_all()
            if student.get("programa_id") == programa_id
        ]

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


def _user(role: str, uid: str) -> CurrentUser:
    return CurrentUser(
        uid=uid,
        role=role,
        programa_id="prog",
        email=f"{role}@saga.test",
    )


def _service(repo: _FakeExtensionRepository | None = None) -> ExtensionService:
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
async def test_list_extensions_aluno_ve_apenas_proprias() -> None:
    result = await _service().list_extensions(_user("aluno", "uid-aluno"))

    assert [item["id"] for item in result] == ["ext1"]
    assert result[0]["aluno_nome"] == "Aluno Um"


@pytest.mark.asyncio
async def test_list_extensions_orientador_ve_orientandos() -> None:
    result = await _service().list_extensions(_user("orientador", "uid-orientador"))

    assert [item["id"] for item in result] == ["ext1"]


@pytest.mark.asyncio
async def test_list_extensions_coordenacao_ve_todas() -> None:
    result = await _service().list_extensions(_user("coordenacao", "uid-coord"))

    assert [item["id"] for item in result] == ["ext1", "ext2"]


@pytest.mark.asyncio
async def test_list_pending_for_coordination_filtra_programa_e_status_default() -> None:
    result = await _service(_MixedExtensionRepository()).list_pending_for_coordination(
        _user("coordenacao", "uid-coord")
    )

    # default status=pendente; só do programa "prog" (ext3 é aprovada, ext4 é de outro programa)
    assert {item["id"] for item in result} == {"ext1", "ext2"}
    nomes = {item["id"]: item["aluno_nome"] for item in result}
    assert nomes["ext1"] == "Aluno Um"
    assert nomes["ext2"] == "Aluno Dois"


@pytest.mark.asyncio
async def test_list_pending_for_coordination_aceita_outro_status() -> None:
    result = await _service(_MixedExtensionRepository()).list_pending_for_coordination(
        _user("coordenacao", "uid-coord"), status="aprovada"
    )

    assert {item["id"] for item in result} == {"ext3"}


@pytest.mark.asyncio
async def test_create_extension_aluno_usa_aluno_autenticado() -> None:
    repo = _FakeExtensionRepository()
    result = await _service(repo).create_extension(
        ExtensionCreateRequest(
            tipo="prazo_defesa",
            nova_data=date(2028, 7, 1),
            motivo="Ajuste de cronograma",
        ),
        _user("aluno", "uid-aluno"),
    )

    assert result["id"] == "ext_new"
    assert repo.created is not None
    assert repo.created["student_id"] == "student1"


@pytest.mark.asyncio
async def test_create_extension_orientador_bloqueia_aluno_fora_da_orientacao() -> None:
    with pytest.raises(HTTPException) as exc:
        await _service().create_extension(
            ExtensionCreateRequest(
                tipo="prazo_defesa",
                student_id="student2",
                nova_data=date(2028, 7, 1),
                motivo="Ajuste de cronograma",
            ),
            _user("orientador", "uid-orientador"),
        )

    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_create_extension_bloqueia_pendente_duplicada() -> None:
    with pytest.raises(HTTPException) as exc:
        await _service(_PendingExtensionRepository()).create_extension(
            ExtensionCreateRequest(
                tipo="prazo_defesa",
                nova_data=date(2028, 7, 1),
                motivo="Ajuste de cronograma",
            ),
            _user("aluno", "uid-aluno"),
        )

    assert exc.value.status_code == 409


@pytest.mark.parametrize(
    "tipo",
    ["prazo_defesa", "prazo_qualificacao", "trancamento", "mudanca_nivel"],
)
def test_extension_request_aceita_tipos_validos(tipo: str) -> None:
    request = ExtensionCreateRequest(
        tipo=tipo, nova_data=date(2028, 7, 1), motivo="Ajuste"
    )

    assert request.tipo == tipo


def test_extension_request_rejeita_tipo_invalido() -> None:
    with pytest.raises(ValidationError):
        ExtensionCreateRequest(
            tipo="qualquer", nova_data=date(2028, 7, 1), motivo="Ajuste"
        )


def test_extension_request_exige_tipo() -> None:
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
