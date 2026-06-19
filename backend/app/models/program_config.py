"""
Modelos Pydantic para configurações de programas acadêmicos.

Responsabilidades:
- Definir a estrutura para dados de configuração do programa (créditos, prazos, prorrogações).
- Fornecer validação para atualizações de configuração.
- Permitir mapeamento direto entre documentos Firestore e objetos Python.
"""

from pydantic import BaseModel, ConfigDict


class ProgramConfigBase(BaseModel):
    """Schema base para configurações de programas.

    Attributes:
        creditos_grupo_basico_min: Créditos mínimos exigidos para o grupo básico.
        creditos_grupo_especifico_min: Créditos mínimos exigidos para o grupo específico.
        creditos_grupo_tecnologico_max: Máximo de créditos permitidos para o grupo tecnológico.
        creditos_total_min: Mínimo total de créditos exigidos para o programa.
        max_prorrogacoes: Número máximo de prorrogações permitidas para os alunos.
        duracao_prorrogacao_meses: Duração de cada prorrogação em meses.
        meses_ate_qualificacao: Número padrão de meses até a qualificação.
    """
    creditos_grupo_basico_min: int
    creditos_grupo_especifico_min: int
    creditos_grupo_tecnologico_max: int
    creditos_total_min: int
    max_prorrogacoes: int
    duracao_prorrogacao_meses: int
    meses_ate_qualificacao: int


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
    duracao_prorrogacao_meses: int | None = None
    meses_ate_qualificacao: int | None = None


class ProgramConfig(ProgramConfigBase):
    """Representação completa de uma configuração de programa, incluindo seu ID."""
    model_config = ConfigDict(from_attributes=True)

    id: str
