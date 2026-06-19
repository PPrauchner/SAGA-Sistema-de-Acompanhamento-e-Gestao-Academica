"""
Modelos Pydantic para níveis de relevância de veículos dentro de um programa.

Responsabilidades:
- Definir a estrutura para mapear veículos para níveis de relevância e pesos específicos.
- Garantir segurança de tipo para lógica de negócios relacionada a relevância.
"""

from pydantic import BaseModel, ConfigDict


class VehicleLevelBase(BaseModel):
    """Schema base para níveis de relevância de veículos.

    Attributes:
        veiculo_id: O identificador único do veículo.
        nivel: O nível de relevância (ex: 'A1', 'A2', 'B1').
        peso: O peso numérico atribuído a este nível para pontuação (RL05).
    """
    veiculo_id: str
    nivel: str
    peso: float


class VehicleLevelCreate(VehicleLevelBase):
    """Schema para criar um novo mapeamento de nível de veículo."""
    pass


class VehicleLevelUpdate(BaseModel):
    """Schema para atualizar um mapeamento de nível de veículo existente."""
    nivel: str | None = None
    peso: float | None = None


class VehicleLevel(VehicleLevelBase):
    """Representação completa de um mapeamento de nível de veículo, incluindo seu ID no Firestore."""
    model_config = ConfigDict(from_attributes=True)

    id: str
