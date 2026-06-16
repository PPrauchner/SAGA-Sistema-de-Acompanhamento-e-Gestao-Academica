"""
Modelos Pydantic para a entidade ActivityType (tipo de atividade creditável).

Responsabilidades:
- Definir ActivityTypeCreateRequest para POST /api/v1/activity-types com campos: nome,
  categoria, pontuacao_base, limite_maximo_creditos, exige_comprovante, permite_multiplas.
- Definir ActivityTypeUpdateRequest para PUT /api/v1/activity-types/{type_id} (campos
  opcionais editáveis) — aciona o aspecto A03 (@track_history).
- Definir ActivityTypeToggleRequest para PATCH /api/v1/activity-types/{type_id}/toggle —
  também aciona @track_history.
- Definir ActivityTypeResponse para leitura, incluindo ativo (default true).
- Mapear a coleção raiz Firestore activity_types/.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

ActivityCategory = Literal["basico", "especifico", "tecnologico"]


class ActivityTypeCreateRequest(BaseModel):
    nome: str
    categoria: ActivityCategory
    pontuacao_base: float
    limite_maximo_creditos: float | None = None
    exige_comprovante: bool = True
    permite_multiplas: bool = True


class ActivityTypeUpdateRequest(BaseModel):
    nome: str | None = None
    pontuacao_base: float | None = None
    limite_maximo_creditos: float | None = None
    exige_comprovante: bool | None = None
    permite_multiplas: bool | None = None
    observacao: str | None = None


class ActivityTypeToggleRequest(BaseModel):
    ativo: bool
    observacao: str | None = None


class ActivityTypeResponse(BaseModel):
    id: str

    nome: str
    categoria: ActivityCategory

    pontuacao_base: float
    limite_maximo_creditos: float | None = None

    exige_comprovante: bool
    permite_multiplas: bool
    ativo: bool = True
