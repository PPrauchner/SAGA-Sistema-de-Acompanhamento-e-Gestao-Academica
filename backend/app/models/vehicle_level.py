"""
Pydantic models for vehicle relevance levels within a program.

Responsabilidades:
- Define the structure for mapping vehicles to specific relevance levels and weights.
- Ensure type safety for relevance-related business logic.
"""

from pydantic import BaseModel, ConfigDict


class VehicleLevelBase(BaseModel):
    """Base schema for vehicle relevance levels.

    Attributes:
        veiculo_id: The unique identifier of the vehicle.
        nivel: The relevance level (e.g., 'A1', 'A2', 'B1').
        peso: The numeric weight assigned to this level for scoring (RL05).
    """
    veiculo_id: str
    nivel: str
    peso: float


class VehicleLevelCreate(VehicleLevelBase):
    """Schema for creating a new vehicle level mapping."""
    pass


class VehicleLevelUpdate(BaseModel):
    """Schema for updating an existing vehicle level mapping."""
    nivel: str | None = None
    peso: float | None = None


class VehicleLevel(VehicleLevelBase):
    """Full representation of a vehicle level mapping, including its Firestore ID."""
    model_config = ConfigDict(from_attributes=True)

    id: str
