"""
Pydantic models for academic program configurations.

Responsabilidades:
- Define the structure for program configuration data (credits, deadlines, extensions).
- Provide validation for configuration updates.
- Enable seamless mapping between Firestore documents and Python objects.
"""

from pydantic import BaseModel, ConfigDict


class ProgramConfigBase(BaseModel):
    """Base schema for program configurations.

    Attributes:
        creditos_grupo_basico_min: Minimum credits required for the basic group.
        creditos_grupo_especifico_min: Minimum credits required for the specific group.
        creditos_grupo_tecnologico_max: Maximum credits allowed for the technological group.
        creditos_total_min: Minimum total credits required for the program.
        max_prorrogacoes: Maximum number of extensions allowed for students.
        duracao_prorrogacao_meses: Duration of each extension in months.
        meses_ate_qualificacao: Standard number of months until qualification.
    """
    creditos_grupo_basico_min: int
    creditos_grupo_especifico_min: int
    creditos_grupo_tecnologico_max: int
    creditos_total_min: int
    max_prorrogacoes: int
    duracao_prorrogacao_meses: int
    meses_ate_qualificacao: int


class ProgramConfigCreate(ProgramConfigBase):
    """Schema for creating a new program configuration."""
    pass


class ProgramConfigUpdate(BaseModel):
    """Schema for updating an existing program configuration.

    All fields are optional to support partial updates (PATCH/PUT).
    """
    creditos_grupo_basico_min: int | None = None
    creditos_grupo_especifico_min: int | None = None
    creditos_grupo_tecnologico_max: int | None = None
    creditos_total_min: int | None = None
    max_prorrogacoes: int | None = None
    duracao_prorrogacao_meses: int | None = None
    meses_ate_qualificacao: int | None = None


class ProgramConfig(ProgramConfigBase):
    """Full representation of a program configuration, including its ID."""
    model_config = ConfigDict(from_attributes=True)

    id: str
