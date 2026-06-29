from __future__ import annotations

from datetime import date
from typing import Any

import pytest
from fastapi import HTTPException

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


class _PendingExtensionRepository(_FakeExtensionRepository):
    async def has_pending_for_student(self, student_id: str) -> bool:
        return True


class _FakeStudentRepository:
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
