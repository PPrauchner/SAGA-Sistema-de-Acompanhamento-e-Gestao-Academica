"""
Serviço de negócio para upload de comprovantes de atividade ao Firebase Storage.

Responsabilidades:
- upload(): valida tipo (PDF/JPEG/PNG) e tamanho máximo do arquivo enviado, resolve o
  student_id do aluno autenticado, confere que a atividade existe (e pertence ao aluno),
  delega a persistência ao StorageRepository gravando o arquivo em
  comprovantes/{programa_id}/{student_id}/{activity_id}/{filename} e grava a comprovante_url
  resultante de volta no documento da atividade.
- Devolve a URL de download tokenizada gerada pelo StorageRepository — o frontend nunca
  escreve direto no Storage.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import PurePosixPath

from fastapi import HTTPException, UploadFile, status

from backend.app.core.auth import CurrentUser
from backend.app.repositories.activity_repository import ActivityRepository
from backend.app.repositories.storage_repository import StorageRepository
from backend.app.repositories.student_repository import StudentRepository

ALLOWED_CONTENT_TYPES = {"application/pdf", "image/jpeg", "image/png"}
MAX_COMPROVANTE_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB


class ComprovanteService:
    """Serviço de negócio para upload de comprovantes ao Firebase Storage."""

    def __init__(self) -> None:
        self._students = StudentRepository()
        self._activities = ActivityRepository()
        self._storage = StorageRepository()

    async def upload(
        self,
        activity_id: str,
        arquivo: UploadFile,
        user: CurrentUser,
    ) -> dict:
        """Valida e persiste o comprovante da atividade no Storage.

        Args:
            activity_id: ID da atividade à qual o comprovante pertence (não validado aqui).
            arquivo: Arquivo enviado (PDF/JPEG/PNG, até MAX_COMPROVANTE_SIZE_BYTES).
            user: Aluno autenticado dono do comprovante.

        Returns:
            dict com comprovante_url (URL de download tokenizada) e path_bucket.

        Raises:
            HTTPException: 415 (tipo não suportado), 413 (excede tamanho) ou 404 (aluno ou
                atividade não encontrados).
        """
        if arquivo.content_type not in ALLOWED_CONTENT_TYPES:
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail="Tipo de arquivo não suportado (use PDF, JPEG ou PNG)",
            )

        if arquivo.size is not None and arquivo.size > MAX_COMPROVANTE_SIZE_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                detail="Arquivo excede o tamanho máximo de 5MB",
            )

        student_id = await self._resolve_student_id(user)
        activity = await self._activities.get_activity(student_id, activity_id)
        if activity is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Atividade não encontrada",
            )

        content = await arquivo.read()
        if len(content) > MAX_COMPROVANTE_SIZE_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                detail="Arquivo excede o tamanho máximo de 5MB",
            )

        filename = self._safe_filename(arquivo.filename)
        path_bucket = (
            f"comprovantes/{user.programa_id}/{student_id}/{activity_id}/{filename}"
        )

        comprovante_url = await self._storage.upload(
            path_bucket, content, arquivo.content_type
        )

        await self._activities.update_activity(
            student_id,
            activity_id,
            {
                "comprovante_url": comprovante_url,
                "atualizado_em": datetime.now(timezone.utc),
            },
        )

        return {
            "comprovante_url": comprovante_url,
            "path_bucket": path_bucket,
        }

    @staticmethod
    def _safe_filename(filename: str | None) -> str:
        """Reduz o filename do cliente ao basename, impedindo que `/` ou `..` desloquem
        o objeto para fora do prefixo {programa_id}/{student_id}/{activity_id} no bucket."""
        normalized = (filename or "").replace("\\", "/")
        base = PurePosixPath(normalized).name
        return base or f"comprovante-{uuid.uuid4().hex}"

    async def _resolve_student_id(self, user: CurrentUser) -> str:
        """Resolve o student_id (auto-id) do aluno autenticado pelo seu uid."""
        students = await self._students.list_all()

        student = next(
            (item for item in students if item.get("uid") == user.uid),
            None,
        )

        if student is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Aluno não encontrado",
            )

        return student["id"]
