"""
Modelos Pydantic para a entidade Department (departamento).

Responsabilidades:
- Definir DepartmentCreateRequest/DepartmentUpdateRequest para o CRUD restrito a `adm`
  (POST/PUT /api/v1/departments).
- Definir DepartmentResponse para leitura, mapeando a coleção raiz Firestore departments/.
- Departamento é entidade global à instituição (ADR-0004): sem `programa_id` — é o
  programa que referencia o departamento (`programa.departamento_id`), nunca o inverso.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class DepartmentCreateRequest(BaseModel):
    nome: str = Field(..., min_length=1)
    instituicao: str | None = None


class DepartmentUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nome: str | None = Field(default=None, min_length=1)
    instituicao: str | None = None


class DepartmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    nome: str
    instituicao: str | None = None
    criado_em: datetime | None = None
    atualizado_em: datetime | None = None
