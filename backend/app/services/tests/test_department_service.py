"""
Testes para DepartmentService — CRUD e o guard de exclusão contra programas vinculados
(ADR-0004).
"""

from __future__ import annotations

from typing import Any

import pytest
from fastapi import HTTPException

from backend.app.models.department import (
    DepartmentCreateRequest,
    DepartmentUpdateRequest,
)
from backend.app.services.department_service import DepartmentService


class _FakeDepartmentRepository:
    store: dict[str, dict[str, Any]] = {}
    counter = 0
    linked_to_programs: set[str] = set()

    async def create(self, data: dict[str, Any]) -> str:
        type(self).counter += 1
        doc_id = f"dept{type(self).counter}"
        type(self).store[doc_id] = dict(data)
        return doc_id

    async def get(self, doc_id: str) -> dict[str, Any] | None:
        data = type(self).store.get(doc_id)
        return {"id": doc_id, **data} if data is not None else None

    async def update(self, doc_id: str, data: dict[str, Any]) -> None:
        type(self).store.setdefault(doc_id, {}).update(data)

    async def delete(self, doc_id: str) -> None:
        type(self).store.pop(doc_id, None)

    async def list_all(self) -> list[dict[str, Any]]:
        return [{"id": key, **value} for key, value in type(self).store.items()]

    async def has_programs(self, department_id: str) -> bool:
        return department_id in type(self).linked_to_programs


@pytest.fixture(autouse=True)
def _reset() -> None:
    _FakeDepartmentRepository.store = {}
    _FakeDepartmentRepository.counter = 0
    _FakeDepartmentRepository.linked_to_programs = set()


@pytest.fixture
def service() -> DepartmentService:
    return DepartmentService(repository=_FakeDepartmentRepository())


async def test_create_department_persiste_e_retorna_id(service: DepartmentService) -> None:
    result = await service.create_department(
        DepartmentCreateRequest(nome="Ciência da Computação")
    )

    assert result["id"] == "dept1"
    assert _FakeDepartmentRepository.store["dept1"]["nome"] == "Ciência da Computação"
    assert "criado_em" in _FakeDepartmentRepository.store["dept1"]


async def test_list_departments_retorna_todos(service: DepartmentService) -> None:
    await service.create_department(DepartmentCreateRequest(nome="A"))
    await service.create_department(DepartmentCreateRequest(nome="B"))

    result = await service.list_departments()

    assert {item["nome"] for item in result} == {"A", "B"}


async def test_get_department_inexistente_levanta_404(service: DepartmentService) -> None:
    with pytest.raises(HTTPException) as exc_info:
        await service.get_department("nao-existe")

    assert exc_info.value.status_code == 404


async def test_update_department_altera_campos_informados(service: DepartmentService) -> None:
    created = await service.create_department(DepartmentCreateRequest(nome="Antigo"))

    await service.update_department(created["id"], DepartmentUpdateRequest(nome="Novo"))

    assert _FakeDepartmentRepository.store[created["id"]]["nome"] == "Novo"


async def test_update_department_inexistente_levanta_404(service: DepartmentService) -> None:
    with pytest.raises(HTTPException) as exc_info:
        await service.update_department("nao-existe", DepartmentUpdateRequest(nome="X"))

    assert exc_info.value.status_code == 404


async def test_delete_department_sem_programas_remove(service: DepartmentService) -> None:
    created = await service.create_department(DepartmentCreateRequest(nome="A remover"))

    await service.delete_department(created["id"])

    assert created["id"] not in _FakeDepartmentRepository.store


async def test_delete_department_com_programa_vinculado_rejeita(
    service: DepartmentService,
) -> None:
    created = await service.create_department(DepartmentCreateRequest(nome="Com programa"))
    _FakeDepartmentRepository.linked_to_programs.add(created["id"])

    with pytest.raises(HTTPException) as exc_info:
        await service.delete_department(created["id"])

    assert exc_info.value.status_code == 400
    assert created["id"] in _FakeDepartmentRepository.store
