"""
Repository for academic activity types.

Responsabilidades:
- Implement CRUD operations for the 'activity_types' collection.
- Filter activity types by program.
"""

from typing import Any, Dict, List, Optional
from backend.app.repositories.firebase_repository import FirebaseRepository


class ActivityTypeRepository(FirebaseRepository):
    """Concrete repository for activity types in Firestore."""

    def __init__(self):
        """Initializes the ActivityTypeRepository."""
        super().__init__()
        self.collection = "activity_types"

    def get_all_by_program(self, programa_id: str) -> List[Dict[str, Any]]:
        """Fetches all activity types belonging to a specific program.

        Args:
            programa_id: The unique identifier of the program.

        Returns:
            A list of activity type documents.
        """
        return self.query(self.collection, filters=[("programa_id", "==", programa_id)])

    def get_type(self, type_id: str) -> Optional[Dict[str, Any]]:
        """Fetches a single activity type by ID.

        Args:
            type_id: The unique identifier of the activity type.

        Returns:
            The activity type data or None.
        """
        return self.get(self.collection, type_id)

    def create_type(self, data: Dict[str, Any]) -> str:
        """Creates a new activity type.

        Args:
            data: The activity type data.

        Returns:
            The ID of the created document.
        """
        return self.create(self.collection, data)

    def update_type(self, type_id: str, data: Dict[str, Any]) -> bool:
        """Updates an existing activity type.

        Args:
            type_id: The unique identifier of the activity type.
            data: The fields to update.

        Returns:
            True if the update was successful.
        """
        return self.update(self.collection, type_id, data)
