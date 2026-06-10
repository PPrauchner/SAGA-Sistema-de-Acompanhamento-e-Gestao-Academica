"""
Pydantic models for activity types.

Responsabilidades:
- Define the structure for types of creditable activities (articles, courses, etc.).
- Provide validation for activity type creation and updates.
- Include program context to support multi-tenancy.
"""

from pydantic import BaseModel, ConfigDict, Field


class ActivityTypeBase(BaseModel):
    """Base schema for activity types.

    Attributes:
        nome: Descriptive name of the activity type.
        categoria: Group category ('basico', 'especifico', 'tecnologico').
        pontuacao_base: Base credits/points awarded for this activity.
        limite_maximo_creditos: Optional ceiling for credits in this type/category.
        exige_comprovante: Whether a proof document (URL) is mandatory.
        ativo: Whether this type is currently active for the program.
        programa_id: The ID of the program this type belongs to.
    """
    nome: str
    categoria: str = Field(..., pattern="^(basico|especifico|tecnologico)$")
    pontuacao_base: float
    limite_maximo_creditos: float | None = None
    exige_comprovante: bool = True
    ativo: bool = True
    programa_id: str


class ActivityTypeCreate(ActivityTypeBase):
    """Schema for creating a new activity type."""
    pass


class ActivityTypeUpdate(BaseModel):
    """Schema for updating an existing activity type."""
    nome: str | None = None
    categoria: str | None = Field(None, pattern="^(basico|especifico|tecnologico)$")
    pontuacao_base: float | None = None
    limite_maximo_creditos: float | None = None
    exige_comprovante: bool | None = None
    ativo: bool | None = None


class ActivityType(ActivityTypeBase):
    """Full representation of an activity type, including its Firestore ID."""
    model_config = ConfigDict(from_attributes=True)

    id: str
