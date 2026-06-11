"""
Service for managing academic program configurations and vehicle levels.

Responsabilidades:
- Retrieve and update program-wide configurations (credits, deadlines).
- Manage vehicle relevance levels for specific programs.
- Coordinate with ProgramRepository for data persistence.
"""

from typing import Any, Dict, List, Optional
from backend.app.models.program_config import ProgramConfigUpdate
from backend.app.models.vehicle_level import VehicleLevelUpdate, VehicleLevelCreate
from backend.app.repositories.program_repository import ProgramRepository


class ProgramService:
    """Service to handle business logic for program configurations."""

    def __init__(self, repository: Optional[ProgramRepository] = None):
        """Initializes the ProgramService.

        Args:
            repository: An instance of ProgramRepository. If None, a new one is created.
        """
        self.repository = repository or ProgramRepository()

    def get_config(self, programa_id: str) -> Optional[Dict[str, Any]]:
        """Fetches the configuration for a given program.

        Args:
            programa_id: The unique identifier of the program.

        Returns:
            The program configuration as a dictionary or None.
        """
        return self.repository.get_config(programa_id)

    def update_config(self, programa_id: str, data: ProgramConfigUpdate) -> bool:
        """Updates the configuration for a given program.

        Args:
            programa_id: The unique identifier of the program.
            data: The update data validated by Pydantic.

        Returns:
            True if the update was successful.
        """
        update_dict = data.model_dump(exclude_unset=True)
        return self.repository.update_config(programa_id, update_dict)

    def get_vehicle_levels(self, programa_id: str) -> List[Dict[str, Any]]:
        """Fetches all vehicle relevance levels for a program.

        Args:
            programa_id: The unique identifier of the program.

        Returns:
            A list of vehicle level mappings.
        """
        return self.repository.get_vehicle_levels(programa_id)

    def update_vehicle_level(
        self, 
        programa_id: str, 
        veiculo_id: str, 
        data: VehicleLevelUpdate | VehicleLevelCreate
    ) -> bool:
        """Updates or creates a vehicle relevance level mapping.

        Args:
            programa_id: The unique identifier of the program.
            veiculo_id: The unique identifier of the vehicle.
            data: The level and weight data validated by Pydantic.

        Returns:
            True if the update was successful.
        """
        update_dict = data.model_dump(exclude_unset=True)
        return self.repository.update_vehicle_level(programa_id, veiculo_id, update_dict)
