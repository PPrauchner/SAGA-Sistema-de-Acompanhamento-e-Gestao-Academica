"""
Modelos Pydantic para a entidade Advisor (orientador).

Responsabilidades:
- Definir AdvisorBase com campos: uid, nome, email, departamento, lattes, programa_id,
  limite_orientandos.
- Definir AdvisorCreate para POST /api/v1/advisors.
- Definir AdvisorUpdate para PUT /api/v1/advisors/{id} (campos opcionais).
- Definir AdvisorResponse para leitura, incluindo orientandos_ativos (calculado por query
  na coleção students/ filtrando por orientador_id).
- Mapear o documento Firestore da coleção advisors/.
"""

from __future__ import annotations

from pydantic import BaseModel


class AdvisorCreateRequest(BaseModel):
    uid: str | None = None
    nome: str
    email: str
    departamento: str

    lattes: str | None = None
    programa_id: str

    limite_orientandos: int = 5


class AdvisorUpdateRequest(BaseModel):
    nome: str | None = None
    departamento: str | None = None

    lattes: str | None = None
    limite_orientandos: int | None = None


class AdvisorResponse(BaseModel):
    id: str
    uid: str

    nome: str
    email: str

    departamento: str
    programa_id: str

    lattes: str | None = None

    limite_orientandos: int
    orientandos_ativos: int
