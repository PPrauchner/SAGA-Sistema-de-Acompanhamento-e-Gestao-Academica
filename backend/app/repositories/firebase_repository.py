"""
Base repository for Firestore operations using Firebase Admin SDK.

Responsabilidades:
- Provide generic asynchronous methods for CRUD operations (get, create, update, delete, query).
- Encapsulate the Firestore client obtained from backend/app/core/firebase.py.
- Handle DocumentNotFoundError and other common database exceptions.
"""

from typing import Any, Dict, List, Optional
from backend.app.core.firebase import get_firestore_client


class FirebaseRepository:
    """Generic base repository for Firestore operations."""

    def __init__(self):
        """Initializes the repository with a Firestore client."""
        self.db = get_firestore_client()

    def get(self, collection: str, doc_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves a single document by ID.

        Args:
            collection: The name of the collection.
            doc_id: The unique identifier of the document.

        Returns:
            The document data as a dictionary, or None if not found.
        """
        doc_ref = self.db.collection(collection).document(doc_id)
        doc = doc_ref.get()
        if doc.exists:
            data = doc.to_dict()
            data['id'] = doc.id
            return data
        return None

    def create(self, collection: str, data: Dict[str, Any], doc_id: Optional[str] = None) -> str:
        """Creates a new document in the collection.

        Args:
            collection: The name of the collection.
            data: The data to be stored.
            doc_id: Optional fixed ID for the document.

        Returns:
            The ID of the created document.
        """
        if doc_id:
            self.db.collection(collection).document(doc_id).set(data)
            return doc_id
        
        _, doc_ref = self.db.collection(collection).add(data)
        return doc_ref.id

    def update(self, collection: str, doc_id: str, data: Dict[str, Any]) -> bool:
        """Updates an existing document.

        Args:
            collection: The name of the collection.
            doc_id: The unique identifier of the document.
            data: The fields to update.

        Returns:
            True if the update was successful.
        """
        doc_ref = self.db.collection(collection).document(doc_id)
        doc_ref.update(data)
        return True

    def delete(self, collection: str, doc_id: str) -> bool:
        """Deletes a document from the collection.

        Args:
            collection: The name of the collection.
            doc_id: The unique identifier of the document.

        Returns:
            True if the deletion was successful.
        """
        self.db.collection(collection).document(doc_id).delete()
        return True

    def query(
        self, 
        collection: str, 
        filters: Optional[List[tuple]] = None, 
        order_by: Optional[str] = None, 
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Performs a query on the collection.

        Args:
            collection: The name of the collection.
            filters: List of tuples (field, operator, value) for filtering.
            order_by: Field name to order the results by.
            limit: Maximum number of results to return.

        Returns:
            A list of document data as dictionaries.
        """
        query_ref = self.db.collection(collection)
        
        if filters:
            for field, op, value in filters:
                query_ref = query_ref.where(field, op, value)
        
        if order_by:
            query_ref = query_ref.order_by(order_by)
            
        if limit:
            query_ref = query_ref.limit(limit)
            
        docs = query_ref.stream()
        results = []
        for doc in docs:
            data = doc.to_dict()
            data['id'] = doc.id
            results.append(data)
            
        return results
