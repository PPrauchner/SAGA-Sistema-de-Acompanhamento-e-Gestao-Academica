"""
Serviço de negócio para gestão de departamentos (ADR-0004).

Responsabilidades:
- Implementar CRUD completo de departamentos delegando persistência ao
  DepartmentRepository. Departamento é entidade global à instituição — não há
  escopo por programa_id nem por papel além de `adm` (autorização em @requires_role
  no router).
- Bloquear a exclusão de um departamento que ainda tem programas vinculados
  (`programa.departamento_id`), análogo ao guard de AdvisorService.delete_advisor
  contra orientandos ativos.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException, status

from backend.app.models.department import (
    DepartmentCreateRequest,
    DepartmentUpdateRequest,
)
from backend.app.repositories.department_repository import DepartmentRepository


class DepartmentService:
    """Serviço para lidar com a lógica de negócio de departamentos."""

    def __init__(self, repository: DepartmentRepository | None = None) -> None:
        self._departments = repository or DepartmentRepository()

    async def list_departments(self) -> list[dict[str, Any]]:
        """Lista todos os departamentos cadastrados."""
        return await self._departments.list_all()

    async def get_department(self, department_id: str) -> dict[str, Any]:
        """Busca um departamento por id.

        Raises:
            HTTPException: 404 se o departamento não existir.
        """
        department = await self._get_or_404(department_id)
        return department

    async def create_department(self, data: DepartmentCreateRequest) -> dict[str, Any]:
        """Cria um novo departamento.

        Args:
            data: Dados validados pelo Pydantic.

        Returns:
            O id do documento criado e os dados persistidos.
        """
        now = datetime.now(timezone.utc)
        payload = {
            **data.model_dump(),
            "criado_em": now,
            "atualizado_em": now,
        }
        department_id = await self._departments.create(payload)
        return {"id": department_id, **payload}

    async def update_department(
        self,
        department_id: str,
        data: DepartmentUpdateRequest,
    ) -> dict[str, Any]:
        """Atualiza campos editáveis de um departamento existente.

        Raises:
            HTTPException: 404 se o departamento não existir.
        """
        await self._get_or_404(department_id)

        update_dict = data.model_dump(exclude_unset=True)
        update_dict["atualizado_em"] = datetime.now(timezone.utc)
        await self._departments.update(department_id, update_dict)

        return {"message": "Departamento atualizado"}

    async def delete_department(self, department_id: str) -> dict[str, Any]:
        """Remove um departamento, se não houver programa vinculado a ele.

        Raises:
            HTTPException: 404 se o departamento não existir; 400 se houver
                programa(s) vinculado(s) (`programa.departamento_id`).
        """
        await self._get_or_404(department_id)

        if await self._departments.has_programs(department_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Departamento possui programas vinculados",
            )

        await self._departments.delete(department_id)
        return {"message": "Departamento removido"}

    async def _get_or_404(self, department_id: str) -> dict[str, Any]:
        department = await self._departments.get(department_id)
        if department is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Departamento não encontrado",
            )
        return department
