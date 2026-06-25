"""
Camada de serviço — gerencia as regras de negócio e o fluxo de prorrogações.
"""

from __future__ import annotations
from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import HTTPException, status
from google.cloud import firestore
from google.cloud.firestore_v1 import AsyncTransaction

from backend.app.models.extension import (
    ExtensionCreateRequest,
    DecisionRequest,
    ExtensionDocument,
    ExtensionResponse,
    ExtensionStatus,
)
from backend.app.repositories.extension_repository import ExtensionRepository

DEFAULT_MAX_PRORROGACOES: int = 1
DEFAULT_DURACAO_MESES:    int = 6

def _months_to_timedelta(months: int) -> timedelta:
    return timedelta(days=months * 30)

def _to_response(extension_id: str, data: dict) -> ExtensionResponse:
    return ExtensionResponse(
        extension_id=extension_id,
        **{k: v for k, v in data.items() if k != "extension_id"},
    )

class ExtensionService:
    """Serviço de gerenciamento do ciclo de vida das prorrogações de prazos."""

    def __init__(self, repository: Optional[ExtensionRepository] = None) -> None:
        # Correção M3: Injeção do Repository no lugar de chamadas diretas ao db
        self._repo = repository if repository is not None else ExtensionRepository()

    async def _check_limit(self, student_id: str, program_config: dict) -> None:
        max_allowed: int = program_config.get("max_prorrogacoes", DEFAULT_MAX_PRORROGACOES)
        approved_query = (
            self._repo.extensions_col(student_id)
            .where("status", "==", ExtensionStatus.APROVADA.value)
        )
        approved_docs = [d async for d in approved_query.stream()]
        if len(approved_docs) >= max_allowed:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Limite de {max_allowed} prorrogacao(oes) aprovada(s) ja atingido.",
            )

    async def _check_no_pending(self, student_id: str) -> None:
        pending_query = (
            self._repo.extensions_col(student_id)
            .where("status", "==", ExtensionStatus.PENDENTE.value)
        )
        pending_docs = [d async for d in pending_query.stream()]
        if pending_docs:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ja existe uma solicitacao pendente para este aluno.",
            )

    async def create_extension(
        self,
        student_id: str,
        payload: ExtensionCreateRequest,
        requesting_uid: str,
    ) -> ExtensionResponse:
        program_config = await self._repo.get_program_config()

        await self._check_no_pending(student_id)
        await self._check_limit(student_id, program_config)

        doc_data = ExtensionDocument(
            aluno_id=requesting_uid,
            motivo=payload.motivo,
            plano_atualizado=payload.plano_atualizado,
            semestres_solicitados=payload.semestres_solicitados,
            status=ExtensionStatus.PENDENTE,
            criado_em=datetime.now(tz=timezone.utc),
        ).model_dump()

        doc_data["status"] = doc_data["status"].value

        new_ref = self._repo.extensions_col(student_id).document()
        await new_ref.set(doc_data)

        return _to_response(new_ref.id, doc_data)

    async def add_review(
        self,
        student_id: str,
        extension_id: str,
        parecer: str,
        orientador_uid: str,
    ) -> ExtensionResponse:
        student_snap = await self._repo.student_ref(student_id).get()
        if not student_snap.exists:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Aluno nao encontrado.")

        student_data: dict = student_snap.to_dict()
        if student_data.get("orientador_id") != orientador_uid:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Voce nao e o orientador deste discente.",
            )

        ext_ref = self._repo.extensions_col(student_id).document(extension_id)
        ext_snap = await ext_ref.get()
        if not ext_snap.exists:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prorrogacao nao encontrada.")

        ext_data: dict = ext_snap.to_dict()
        if ext_data.get("status") != ExtensionStatus.PENDENTE.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Apenas prorrogacoes pendentes podem receber parecer.",
            )

        await ext_ref.update({"parecer_orientador": parecer})
        ext_data["parecer_orientador"] = parecer

        return _to_response(extension_id, ext_data)

    async def process_decision(
        self,
        student_id: str,
        extension_id: str,
        payload: DecisionRequest,
        coordinator_uid: str,
    ) -> ExtensionResponse:
        ext_ref = self._repo.extensions_col(student_id).document(extension_id)
        student_ref = self._repo.student_ref(student_id)

        program_config = await self._repo.get_program_config()
        duracao_meses: int = program_config.get("duracao_prorrogacao_meses", DEFAULT_DURACAO_MESES)

        @firestore.async_transactional
        async def _run_transaction(transaction: AsyncTransaction) -> dict:
            ext_snap = await transaction.get(ext_ref)
            student_snap = await transaction.get(student_ref)

            if not ext_snap.exists:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prorrogacao nao encontrada.")
            if not student_snap.exists:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Aluno nao encontrado.")

            ext_data: dict = ext_snap.to_dict()
            student_data: dict = student_snap.to_dict()

            if ext_data.get("status") != ExtensionStatus.PENDENTE.value:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Apenas prorrogacoes pendentes podem ser deliberadas.",
                )

            now = datetime.now(tz=timezone.utc)

            # Correção C4/M1: Payload processa o booleano de aprovação regulamentar
            if payload.aprovado:
                semestres: int = ext_data["semestres_solicitados"]
                delta = _months_to_timedelta(semestres * duracao_meses)

                prazo_anterior: Optional[datetime] = student_data.get("prazo_final")
                if prazo_anterior is None:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="O aluno nao possui prazo_final definido.",
                    )

                prazo_novo = prazo_anterior + delta

                ext_updates = {
                    "status": ExtensionStatus.APROVADA.value,
                    "aprovado_por": coordinator_uid,
                    "aprovado_em": now,
                    "prazo_novo": prazo_novo,
                }
                student_updates = {
                    "situacao_registrada": "em_prorrogacao",
                    "prazo_final": prazo_novo,
                }

                transaction.update(ext_ref, ext_updates)
                transaction.update(student_ref, student_updates)
                ext_data.update(ext_updates)
            else:
                ext_updates = {"status": ExtensionStatus.REJEITADA.value}
                transaction.update(ext_ref, ext_updates)
                ext_data.update(ext_updates)

            return ext_data

        transaction = self._repo.transaction()
        final_data = await _run_transaction(transaction)

        return _to_response(extension_id, final_data)

    async def list_by_student(self, student_id: str) -> list[ExtensionResponse]:
        docs = [
            d async for d in self._repo.extensions_col(student_id).order_by("criado_em", direction=firestore.Query.DESCENDING).stream()
        ]
        return [_to_response(d.id, d.to_dict()) for d in docs]

    async def list_pending_for_advisor(self, orientador_uid: str) -> list[ExtensionResponse]:
        students_query = (
            self._repo._db.collection("students")
            .where("orientador_id", "==", orientador_uid)
        )
        results: list[ExtensionResponse] = []
        async for student_doc in students_query.stream():
            pending = (
                self._repo.extensions_col(student_doc.id)
                .where("status", "==", ExtensionStatus.PENDENTE.value)
            )
            async for ext_doc in pending.stream():
                results.append(_to_response(ext_doc.id, ext_doc.to_dict()))
        return results

    async def list_all_pending(self) -> list[ExtensionResponse]:
        query = (
            self._repo.collection_group_extensions()
            .where("status", "==", ExtensionStatus.PENDENTE.value)
            .order_by("criado_em", direction=firestore.Query.ASCENDING)
        )
        return [_to_response(d.id, d.to_dict()) async for d in query.stream()]