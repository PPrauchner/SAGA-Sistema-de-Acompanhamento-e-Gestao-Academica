"""
Repositório concreto para a coleção raiz activity_types/.

Responsabilidades:
- Herdar FirebaseRepository e especializar operações para a coleção activity_types/.
- CRUD básico via get/create/update/delete/list_all herdados de FirebaseRepository.
- save_history_snapshot(type_id, snapshot): herdado de FirebaseRepository, persiste
  snapshot do aspecto A03 em activity_types/{id}/history/{auto_id}.
"""

from __future__ import annotations

from backend.app.repositories.firebase_repository import FirebaseRepository


class ActivityTypeRepository(FirebaseRepository):
    """Repositório específico da coleção activity_types."""

    def __init__(self) -> None:
        super().__init__("activity_types")
