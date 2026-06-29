"""
Serviço de gerenciamento do ciclo de vida das prorrogações de prazos.

Contrato de identidade dos parâmetros student_id:
- create_extension        → recebe uid (do token JWT via current_user.uid)
                            → resolve uid→doc_id via _resolve_student_doc_id
- list_by_student         → recebe doc_id (de /auth/me → studentId no frontend)
- add_review              → recebe doc_id (montado pelo frontend a partir de /auth/me)
- process_decision        → recebe doc_id (idem)

Correção C1: _resolve_student_doc_id removida dos métodos que recebem doc_id
diretamente, eliminando o 404 que impedia o aluno de ver as próprias prorrogações.
"""

import asyncio
from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException, status
from google.cloud import firestore

from backend.app.models.extension import (
    DecisionRequest,
    ExtensionCreateRequest,
    ExtensionDocument,
    ExtensionResponse,
    ExtensionStatus,
)
from backend.app.repositories.extension_repository import ExtensionRepository

DEFAULT_MAX_PRORROGACOES = 3
DEFAULT_DURACAO_MESES = 6


def _months_to_timedelta(months: int):
    from datetime import timedelta
    return timedelta(days=months * 30)


def _to_response(doc_id: str, data: dict) -> ExtensionResponse:
    return ExtensionResponse(id=doc_id, **data)


class ExtensionService:
    """Serviço de gerenciamento do ciclo de vida das prorrogações de prazos."""

    def __init__(self, repository: Optional[ExtensionRepository] = None) -> None:
        self._repo = repository if repository is not None else ExtensionRepository()

    # ------------------------------------------------------------------
    # Helpers internos
    # ------------------------------------------------------------------

    async def _resolve_student_doc_id(self, uid: str) -> str:
        """
        Resolve uid → doc id da coleção students (chaveada por auto-id).
        Usado APENAS em create_extension, onde student_id vem do token JWT.
        Lança 404 se o aluno não existir.
        """
        doc_id = await self._repo.get_student_doc_id_by_uid(uid)
        if doc_id is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Aluno não encontrado.",
            )
        return doc_id

    async def _check_limit(self, student_doc_id: str, program_config: dict) -> None:
        max_allowed: int = program_config.get("max_prorrogacoes", DEFAULT_MAX_PRORROGACOES)
        approved_query = (
            self._repo.extensions_col(student_doc_id)
            .where("status", "==", ExtensionStatus.APROVADA.value)
        )
        approved_docs = [d async for d in approved_query.stream()]
        if len(approved_docs) >= max_allowed:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Limite de {max_allowed} prorrogacao(oes) aprovada(s) ja atingido.",
            )

    async def _check_no_pending(self, student_doc_id: str) -> None:
        pending_query = (
            self._repo.extensions_col(student_doc_id)
            .where("status", "==", ExtensionStatus.PENDENTE.value)
        )
        pending_docs = [d async for d in pending_query.stream()]
        if pending_docs:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ja existe uma solicitacao pendente para este aluno.",
            )

    # ------------------------------------------------------------------
    # Casos de uso
    # ------------------------------------------------------------------

    async def create_extension(
        self,
        student_id: str,
        payload: ExtensionCreateRequest,
        requesting_uid: str,
    ) -> ExtensionResponse:
        # Único método que recebe uid (de current_user.uid no router).
        # _resolve_student_doc_id é correto aqui.
        student_doc_id = await self._resolve_student_doc_id(student_id)

        program_config = await self._repo.get_program_config()

        max_semestres: int = program_config.get("max_prorrogacoes", DEFAULT_MAX_PRORROGACOES)
        if payload.semestres_solicitados > max_semestres:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"semestres_solicitados excede o máximo permitido pelo programa ({max_semestres}).",
            )

        await self._check_no_pending(student_doc_id)
        await self._check_limit(student_doc_id, program_config)

        doc_data = ExtensionDocument(
            aluno_id=requesting_uid,
            motivo=payload.motivo,
            plano_atualizado=payload.plano_atualizado,
            semestres_solicitados=payload.semestres_solicitados,
            status=ExtensionStatus.PENDENTE,
            criado_em=datetime.now(tz=timezone.utc),
        ).model_dump()

        doc_data["status"] = doc_data["status"].value

        new_ref = self._repo.extensions_col(student_doc_id).document()
        await new_ref.set(doc_data)

        return _to_response(new_ref.id, doc_data)

    async def add_review(
        self,
        student_id: str,
        extension_id: str,
        parecer: str,
        orientador_uid: str,
    ) -> ExtensionResponse:
        # C1: student_id já é doc_id (vem do frontend via /auth/me).
        # Resolução uid→doc_id removida — evita 404 espúrio.
        student_doc_id = student_id

        student_snap = await self._repo.student_ref(student_doc_id).get()
        if not student_snap.exists:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Aluno nao encontrado.")

        student_data: dict = student_snap.to_dict()
        advisor_doc_id = await self._repo.get_advisor_doc_id_by_uid(orientador_uid)

        if student_data.get("orientador_id") != advisor_doc_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Voce nao e o orientador deste discente.",
            )

        ext_ref = self._repo.extensions_col(student_doc_id).document(extension_id)
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
        # C1: student_id já é doc_id (vem do frontend via /auth/me).
        # Resolução uid→doc_id removida — evita 404 espúrio.
        student_doc_id = student_id

        # Resolve referências síncronas reais para uso dentro da transação.
        ext_ref_sync     = self._repo.extensions_col(student_doc_id).document(extension_id).sync_ref
        student_ref_sync = self._repo.student_ref(student_doc_id).sync_ref

        program_config = await self._repo.get_program_config()
        duracao_meses: int = program_config.get("duracao_prorrogacao_meses", DEFAULT_DURACAO_MESES)

        # @firestore.transactional decora função SÍNCRONA — correto para Admin SDK.
        @firestore.transactional
        def _run_transaction(transaction) -> dict:
            ext_snap     = transaction.get(ext_ref_sync)
            student_snap = transaction.get(student_ref_sync)

            if not ext_snap.exists:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prorrogacao nao encontrada.")
            if not student_snap.exists:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Aluno nao encontrado.")

            ext_data:     dict = ext_snap.to_dict()
            student_data: dict = student_snap.to_dict()

            if ext_data.get("status") != ExtensionStatus.PENDENTE.value:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Apenas prorrogacoes pendentes podem ser deliberadas.",
                )

            now = datetime.now(tz=timezone.utc)

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
                    "status":       ExtensionStatus.APROVADA.value,
                    "aprovado_por": coordinator_uid,
                    "aprovado_em":  now,
                    "prazo_novo":   prazo_novo,
                }
                student_updates = {
                    "situacao_registrada": "em_prorrogacao",
                    "prazo_final":         prazo_novo,
                }

                transaction.update(ext_ref_sync,     ext_updates)
                transaction.update(student_ref_sync, student_updates)
                ext_data.update(ext_updates)
            else:
                ext_updates = {"status": ExtensionStatus.REJEITADA.value}
                transaction.update(ext_ref_sync, ext_updates)
                ext_data.update(ext_updates)

            return ext_data

        db = self._repo.transaction()
        final_data = await asyncio.to_thread(_run_transaction, db.transaction())

        return _to_response(extension_id, final_data)

    async def list_by_student(self, student_doc_id: str) -> list[ExtensionResponse]:
        # C1: student_doc_id já é o doc_id vindo de /auth/me → studentId no frontend.
        # Resolução uid→doc_id removida — era a causa do 404 que impedia o aluno
        # de ver as próprias prorrogações.
        docs = [
            d async for d in self._repo.extensions_col(student_doc_id)
            .order_by("criado_em", direction=firestore.Query.DESCENDING)
            .stream()
        ]
        return [_to_response(d.id, d.to_dict()) for d in docs]

    async def list_pending_for_advisor(self, orientador_uid: str) -> list[ExtensionResponse]:
        advisor_doc_id = await self._repo.get_advisor_doc_id_by_uid(orientador_uid)
        if advisor_doc_id is None:
            return []

        def _fetch_students() -> list:
            return list(
                self._repo._db
                .collection("students")
                .where("orientador_id", "==", advisor_doc_id)
                .stream()
            )

        student_docs = await asyncio.to_thread(_fetch_students)

        results: list[ExtensionResponse] = []
        for student_doc in student_docs:
            # student_doc.id já é o doc id real — sem necessidade de resolução.
            pending_docs = [
                d async for d in
                self._repo.extensions_col(student_doc.id)
                .where("status", "==", ExtensionStatus.PENDENTE.value)
                .stream()
            ]
            for ext_doc in pending_docs:
                results.append(_to_response(ext_doc.id, ext_doc.to_dict()))

        return results

    async def list_all_pending(self) -> list[ExtensionResponse]:
        query = (
            self._repo.collection_group_extensions()
            .where("status", "==", ExtensionStatus.PENDENTE.value)
            .order_by("criado_em", direction=firestore.Query.ASCENDING)
        )
        return [_to_response(d.id, d.to_dict()) async for d in query.stream()]