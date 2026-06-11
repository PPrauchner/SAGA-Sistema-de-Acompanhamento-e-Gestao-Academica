"""
Service for managing activity types.

Responsabilidades:
- Implement business logic for CRUD operations on activity types.
- Support toggling active status of activity types.
- Coordinate with ActivityTypeRepository for data persistence.
"""

from typing import Any, Dict, List, Optional
from backend.app.models.activity_type import ActivityTypeCreate, ActivityTypeUpdate
from backend.app.repositories.activity_type_repository import ActivityTypeRepository


class ActivityTypeService:
    """Service to handle business logic for activity types."""

    def __init__(self, repository: Optional[ActivityTypeRepository] = None):
        """Initializes the ActivityTypeService.

        Args:
            repository: An instance of ActivityTypeRepository. If None, a new one is created.
        """
        self.repository = repository or ActivityTypeRepository()

    def get_all_by_program(self, programa_id: str) -> List[Dict[str, Any]]:
        """Fetches all activity types belonging to a specific program.

        Args:
            programa_id: The unique identifier of the program.

        Returns:
            A list of activity type documents.
        """
        return self.repository.get_all_by_program(programa_id)

    def create_type(self, data: ActivityTypeCreate) -> str:
        """Creates a new activity type.

        Args:
            data: The activity type data validated by Pydantic.

        Returns:
            The ID of the created document.
        """
        return self.repository.create_type(data.model_dump())

    def update_type(self, type_id: str, data: ActivityTypeUpdate) -> bool:
        """Updates an existing activity type.

        Args:
            type_id: The unique identifier of the activity type.
            data: The update data validated by Pydantic.

        Returns:
            True if the update was successful.
        """
        update_dict = data.model_dump(exclude_unset=True)
        return self.repository.update_type(type_id, update_dict)

    def toggle_active(self, type_id: str) -> bool:
        """Toggles the active status of an activity type.

        Args:
            type_id: The unique identifier of the activity type.

        Returns:
            True if the toggle was successful.
        """
        current_type = self.repository.get_type(type_id)
        if not current_type:
            return False
        
        new_status = not current_type.get("ativo", True)
        return self.repository.update_type(type_id, {"ativo": new_status})
