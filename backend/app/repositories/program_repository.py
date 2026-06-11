"""
Repository for academic program configurations and vehicle levels.

Responsabilidades:
- Implement CRUD operations for the 'programs' collection.
- Manage vehicle relevance levels as sub-collections of a program.
"""

from typing import Any, Dict, List, Optional
from backend.app.repositories.firebase_repository import FirebaseRepository


class ProgramRepository(FirebaseRepository):
    """Concrete repository for program-related data in Firestore."""

    def __init__(self):
        """Initializes the ProgramRepository."""
        super().__init__("programs")

    async def get_config(self, programa_id: str) -> Optional[Dict[str, Any]]:
        """Fetches the configuration for a given program.

        Args:
            programa_id: The unique identifier of the program.

        Returns:
            The program configuration data or None.
        """
        return await self.get(programa_id)

    async def update_config(self, programa_id: str, data: Dict[str, Any]) -> bool:
        """Updates the configuration for a given program.

        Args:
            programa_id: The unique identifier of the program.
            data: The fields to update.

        Returns:
            True if the update was successful.
        """
        return await self.update(programa_id, data)

    async def get_vehicle_levels(self, programa_id: str) -> List[Dict[str, Any]]:
        """Fetches all vehicle relevance levels for a program.

        Args:
            programa_id: The unique identifier of the program.

        Returns:
            A list of vehicle level mappings.
        """
        collection_path = f"{self.collection}/{programa_id}/vehicle_levels"
        return await self.query(subcollection_path=collection_path)

    async def update_vehicle_level(self, programa_id: str, veiculo_id: str, data: Dict[str, Any]) -> bool:
        """Updates or creates a vehicle relevance level mapping.

        Args:
            programa_id: The unique identifier of the program.
            veiculo_id: The unique identifier of the vehicle.
            data: The level and weight data.

        Returns:
            True if the update was successful.
        """
        import asyncio
        from backend.app.core.firebase import get_firestore_client
        collection_path = f"{self.collection}/{programa_id}/vehicle_levels"
        
        def _update():
            # Using the vehicle ID as the document ID for the mapping
            get_firestore_client().collection(collection_path).document(veiculo_id).set(data, merge=True)
            return True
            
        return await asyncio.to_thread(_update)

