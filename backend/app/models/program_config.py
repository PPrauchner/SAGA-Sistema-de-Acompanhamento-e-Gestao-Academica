"""
Modelos Pydantic para configurações de programas acadêmicos.

Responsabilidades:
- Definir a estrutura para dados de configuração do programa (créditos, prazos, prorrogações).
- Fornecer validação para atualizações de configuração.
- Permitir mapeamento direto entre documentos Firestore e objetos Python.
"""

import math
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


CREDIT_FIELDS = {
    "creditos_grupo_basico_min",
    "creditos_grupo_especifico_min",
    "creditos_grupo_tecnologico_max",
    "creditos_total_min",
}

DEFAULT_PROGRAM_CREDIT_CONFIG: dict[str, int] = {
    "creditos_grupo_basico_min": 12,
    "creditos_grupo_especifico_min": 8,
    "creditos_grupo_tecnologico_max": 4,
    "creditos_total_min": 24,
}


def _validate_required_int(value: Any, *, min_value: int, message: str) -> int:
    if value is None or value == "":
        raise ValueError(message)
    if isinstance(value, bool):
        raise ValueError(message)
    if isinstance(value, float) and math.isnan(value):
        raise ValueError(message)
    if not isinstance(value, int):
        raise ValueError(message)
    if value < min_value:
        raise ValueError(message)
    return value


class ProgramConfigBase(BaseModel):
    """Schema base para configurações de programas.

    Attributes:
        departamento_id: Departamento ao qual o programa pertence (ADR-0004) —
            obrigatório na criação; entidade-pai estrutural do programa.
        creditos_grupo_basico_min: Créditos mínimos exigidos para o grupo básico.
        creditos_grupo_especifico_min: Créditos mínimos exigidos para o grupo específico.
        creditos_grupo_tecnologico_max: Máximo de créditos permitidos para o grupo tecnológico.
        creditos_total_min: Mínimo total de créditos exigidos para o programa.
        max_prorrogacoes: Número máximo de prorrogações permitidas para os alunos.
        duracao_meses: Duração regular do programa em meses.
        duracao_prorrogacao_meses: Duração de cada prorrogação em meses.
        meses_ate_qualificacao: Número padrão de meses até a qualificação.
    """
    departamento_id: str = Field(..., min_length=1)
    creditos_grupo_basico_min: int
    creditos_grupo_especifico_min: int
    creditos_grupo_tecnologico_max: int
    creditos_total_min: int
    max_prorrogacoes: int
    duracao_meses: int = 24
    duracao_prorrogacao_meses: int
    meses_ate_qualificacao: int

    @field_validator(*CREDIT_FIELDS, mode="before")
    @classmethod
    def _validate_credit_fields(cls, value: Any) -> int:
        return _validate_required_int(
            value,
            min_value=0,
            message="Créditos devem ser inteiros maiores ou iguais a zero.",
        )

    @field_validator("meses_ate_qualificacao", mode="before")
    @classmethod
    def _validate_meses_ate_qualificacao(cls, value: Any) -> int:
        return _validate_required_int(
            value,
            min_value=1,
            message="Meses até qualificação deve ser maior ou igual a 1.",
        )

    @model_validator(mode="after")
    def _validate_creditos_total_min(self) -> "ProgramConfigBase":
        if self.creditos_total_min < self.creditos_grupo_basico_min + self.creditos_grupo_especifico_min:
            raise ValueError(
                "Créditos totais mínimos não podem ser menores que a soma dos créditos básico e específico."
            )
        return self


class ProgramConfigCreate(ProgramConfigBase):
    """Schema para criar uma nova configuração de programa."""
    pass


class ProgramConfigUpdate(BaseModel):
    """Schema para atualizar uma configuração de programa existente.

    Todos os campos são opcionais para suportar atualizações parciais (PATCH/PUT).
    """
    creditos_grupo_basico_min: int | None = None
    creditos_grupo_especifico_min: int | None = None
    creditos_grupo_tecnologico_max: int | None = None
    creditos_total_min: int | None = None
    max_prorrogacoes: int | None = None
    duracao_meses: int | None = None
    duracao_prorrogacao_meses: int | None = None
    meses_ate_qualificacao: int | None = None

    @field_validator(*CREDIT_FIELDS, mode="before")
    @classmethod
    def _validate_credit_fields(cls, value: Any) -> int:
        return _validate_required_int(
            value,
            min_value=0,
            message="Créditos devem ser inteiros maiores ou iguais a zero.",
        )

    @field_validator("meses_ate_qualificacao", mode="before")
    @classmethod
    def _validate_meses_ate_qualificacao(cls, value: Any) -> int:
        return _validate_required_int(
            value,
            min_value=1,
            message="Meses até qualificação deve ser maior ou igual a 1.",
        )


class ProgramConfig(ProgramConfigBase):
    """Representação completa de uma configuração de programa, incluindo seu ID."""
    model_config = ConfigDict(from_attributes=True)

    id: str
