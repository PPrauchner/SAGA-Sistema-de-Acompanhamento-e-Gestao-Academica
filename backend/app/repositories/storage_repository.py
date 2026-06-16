"""
Repositório de acesso ao Firebase Storage via Admin SDK.

Responsabilidades:
- Encapsular o acesso ao bucket (core/firebase.get_storage_bucket) — única camada que
  importa o cliente de Storage, espelhando o contrato do FirebaseRepository para o Firestore.
- upload(path, content, content_type): persiste o conteúdo no bucket via Admin SDK,
  gravando um token de download em metadata e devolvendo a URL de download tokenizada
  (padrão Firebase Storage). A chamada bloqueante do SDK é executada em thread separada
  via asyncio.to_thread para não bloquear o event loop do FastAPI.
"""

from __future__ import annotations

import asyncio
import uuid
from urllib.parse import quote

from backend.app.core.firebase import get_storage_bucket


class StorageRepository:
    """Repositório de acesso ao bucket do Firebase Storage."""

    async def upload(self, path: str, content: bytes, content_type: str | None) -> str:
        """Persiste o conteúdo no bucket e retorna a URL de download tokenizada.

        Args:
            path: Caminho do objeto dentro do bucket.
            content: Bytes do arquivo a persistir.
            content_type: MIME type do arquivo (gravado no blob).

        Returns:
            URL de download tokenizada (formato firebasestorage.googleapis.com).
        """
        return await asyncio.to_thread(self._upload, path, content, content_type)

    def _upload(self, path: str, content: bytes, content_type: str | None) -> str:
        """Executa o upload bloqueante no bucket e monta a URL de download tokenizada."""
        bucket = get_storage_bucket()
        blob = bucket.blob(path)
        token = str(uuid.uuid4())
        blob.metadata = {"firebaseStorageDownloadTokens": token}
        blob.upload_from_string(content, content_type=content_type)

        return (
            f"https://firebasestorage.googleapis.com/v0/b/{bucket.name}/o/"
            f"{quote(path, safe='')}?alt=media&token={token}"
        )
