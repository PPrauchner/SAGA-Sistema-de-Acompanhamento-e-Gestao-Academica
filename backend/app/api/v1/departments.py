"""
Router FastAPI para os endpoints de gestão de departamentos (ADR-0004).

Responsabilidades:
- GET /api/v1/departments: lista departamentos cadastrados.
- GET /api/v1/departments/{department_id}: busca um departamento por id.
- POST /api/v1/departments: cria departamento.
- PUT /api/v1/departments/{department_id}: atualiza departamento.
- DELETE /api/v1/departments/{department_id}: remove departamento (verificando
  ausência de programas vinculados).
- Toda a rota é restrita a @requires_role('adm') — departamento é entidade global à
  instituição, fora do escopo de qualquer programa (ADR-0001/ADR-0004). Demais papéis
  recebem 403.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, status

from backend.app.aspects.audit import audit_operation
from backend.app.aspects.authorization import requires_role
from backend.app.core.auth import CurrentUser, get_current_user
from backend.app.models.department import (
    DepartmentCreateRequest,
    DepartmentResponse,
    DepartmentUpdateRequest,
)
from backend.app.services.department_service import DepartmentService

router = APIRouter()

service = DepartmentService()


@router.get("/departments", response_model=list[DepartmentResponse])
@requires_role("adm")
async def list_departments(
    user: CurrentUser = Depends(get_current_user),
) -> list[DepartmentResponse]:
    return await service.list_departments()


@router.get("/departments/{department_id}", response_model=DepartmentResponse)
@requires_role("adm")
async def get_department(
    department_id: str,
    user: CurrentUser = Depends(get_current_user),
) -> DepartmentResponse:
    return await service.get_department(department_id)


@router.post("/departments", status_code=status.HTTP_201_CREATED)
@requires_role("adm")
@audit_operation
async def create_department(
    body: DepartmentCreateRequest,
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    return await service.create_department(body)


@router.put("/departments/{department_id}")
@requires_role("adm")
@audit_operation
async def update_department(
    department_id: str,
    body: DepartmentUpdateRequest,
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    return await service.update_department(department_id, body)


@router.delete("/departments/{department_id}")
@requires_role("adm")
@audit_operation
async def delete_department(
    department_id: str,
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    return await service.delete_department(department_id)
