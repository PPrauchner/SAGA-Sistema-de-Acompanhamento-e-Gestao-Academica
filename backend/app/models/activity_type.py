"""
Modelos Pydantic para a entidade ActivityType (tipo de atividade creditável).

Responsabilidades:
- Definir a estrutura para tipos de atividades creditáveis (artigos, disciplinas, etc.).
- Prover validação para criação e atualização de tipos de atividades.
- Incluir contexto do programa para suportar multi-tenancy.
- Mapear a coleção raiz Firestore activity_types/.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ActivityCategory = Literal["basico", "especifico", "tecnologico"]


class ActivityTypeBase(BaseModel):
    """Esquema base para tipos de atividades."""
    nome: str
    categoria: ActivityCategory = Field(..., description="Categoria da atividade (basico, especifico ou tecnologico)")
    pontuacao_base: float
    limite_maximo_creditos: float | None = None
    exige_comprovante: bool = True
    permite_multiplas: bool = True
    ativo: bool = True


class ActivityTypeCreate(ActivityTypeBase):
    """Esquema para criação de um novo tipo de atividade."""
    pass


class ActivityTypeUpdate(BaseModel):
    """Esquema para atualização de um tipo de atividade existente."""
    nome: str | None = None
    categoria: ActivityCategory | None = None
    pontuacao_base: float | None = None
    limite_maximo_creditos: float | None = None
    exige_comprovante: bool | None = None
    permite_multiplas: bool | None = None
    ativo: bool | None = None
    observacao: str | None = None


class ActivityTypeToggleRequest(BaseModel):
    """Esquema para ativar/desativar um tipo de atividade."""
    ativo: bool
    observacao: str | None = None


class ActivityTypeResponse(ActivityTypeBase):
    """Representação completa de um tipo de atividade, incluindo seu ID no Firestore para respostas."""
    model_config = ConfigDict(from_attributes=True)

    id: str


class ActivityType(ActivityTypeBase):
    """Representação completa de um tipo de atividade (legado), incluindo seu ID no Firestore."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    programa_id: str | None = None
