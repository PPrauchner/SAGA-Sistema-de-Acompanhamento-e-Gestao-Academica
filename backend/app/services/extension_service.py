"""
Serviço de negócio para gestão de solicitações de prorrogação de prazo.

Responsabilidades:
- request_extension(): aluno solicita prorrogação. Verifica se não atingiu max_prorrogacoes
  e se não há solicitação pendente. Decorado com @requires_role('aluno'),
  @audit_operation e @check_deadlines.
- advisor_review(): orientador registra parecer sobre a prorrogação.
  Decorado com @requires_role('orientador') e @audit_operation.
- approve_extension(): coordenação aprova ou rejeita. Se aprovada, atualiza prazo_final
  do aluno e registra situacao_registrada='em_prorrogacao'. Decorado com
  @requires_role('coordenacao'), @audit_operation e @trigger_alerts (notifica aluno).
"""
"""
extensions_service.py
Camada de serviço — toda a lógica de negócio e invariantes do módulo de Prorrogações.

Responsabilidades:
    - Cômputo dinâmico de limites (lê programs/prog_default.max_prorrogacoes)
    - Unicidade de análise (bloqueia duplicatas pendentes)
    - Transação atômica de aprovação (altera extension + documento pai do aluno)
    - Cálculo e persistência de prazo_novo
"""

from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import HTTPException, status
from google.cloud import firestore  # type: ignore
from google.cloud.firestore_v1 import AsyncTransaction  # type: ignore

from app.models.extension import (
    ExtensionCreateRequest,
    DecisionRequest,
    ExtensionDocument,
    ExtensionResponse,
    ExtensionStatus,
)

# ---------------------------------------------------------------------------
# Constantes de fallback
# ---------------------------------------------------------------------------
DEFAULT_MAX_PRORROGACOES: int = 1
DEFAULT_DURACAO_MESES:    int = 6


# ---------------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------------

def _months_to_timedelta(months: int) -> timedelta:
    """Converte meses em timedelta aproximado (30 dias/mês)."""
    return timedelta(days=months * 30)


def _to_response(extension_id: str, data: dict) -> ExtensionResponse:
    """Converte um dict vindo do Firestore em ExtensionResponse."""
    return ExtensionResponse(
        extension_id=extension_id,
        **{k: v for k, v in data.items() if k != "extension_id"},
    )


# ---------------------------------------------------------------------------
# Serviço principal
# ---------------------------------------------------------------------------

class ExtensionsService:
    """
    Serviço stateless que recebe o cliente Firestore via injeção de dependência.
    Todos os métodos são async e escritas no banco passam exclusivamente por
    aqui, via Admin SDK (google-cloud-firestore).
    """

    def __init__(self, db: firestore.AsyncClient) -> None:
        self._db = db

    # ------------------------------------------------------------------
    # Helpers de acesso ao Firestore
    # ------------------------------------------------------------------

    def _extensions_col(self, student_id: str):
        return self._db.collection("students").document(student_id).collection("extensions")

    def _student_ref(self, student_id: str):
        return self._db.collection("students").document(student_id)

    async def _get_program_config(self) -> dict:
        """Lê configurações globais do programa."""
        snap = await self._db.collection("programs").document("prog_default").get()
        return snap.to_dict() or {}

    # ------------------------------------------------------------------
    # Regra: Limite máximo de prorrogações aprovadas
    # ------------------------------------------------------------------

    async def _check_limit(self, student_id: str, program_config: dict) -> None:
        max_allowed: int = program_config.get("max_prorrogacoes", DEFAULT_MAX_PRORROGACOES)
        approved_query = (
            self._extensions_col(student_id)
            .where("status", "==", ExtensionStatus.APROVADA.value)
        )
        approved_docs = [d async for d in approved_query.stream()]
        if len(approved_docs) >= max_allowed:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Limite de {max_allowed} prorrogação(ões) aprovada(s) já atingido.",
            )

    # ------------------------------------------------------------------
    # Regra: Unicidade de análise (bloqueia pendente duplicado)
    # ------------------------------------------------------------------

    async def _check_no_pending(self, student_id: str) -> None:
        pending_query = (
            self._extensions_col(student_id)
            .where("status", "==", ExtensionStatus.PENDENTE.value)
        )
        pending_docs = [d async for d in pending_query.stream()]
        if pending_docs:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Já existe uma solicitação pendente para este aluno.",
            )

    # ------------------------------------------------------------------
    # CREATE — Aluno cria solicitação
    # ------------------------------------------------------------------

    async def create_extension(
        self,
        student_id: str,
        payload: ExtensionCreateRequest,
        requesting_uid: str,
    ) -> ExtensionResponse:
        """
        Cria uma nova prorrogação com status 'pendente'.
        Valida unicidade de análise e limite de aprovadas antes de persistir.
        """
        program_config = await self._get_program_config()

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

        # Converte enums para string antes de persistir
        doc_data["status"] = doc_data["status"].value

        new_ref = self._extensions_col(student_id).document()
        await new_ref.set(doc_data)

        return _to_response(new_ref.id, doc_data)

    # ------------------------------------------------------------------
    # REVIEW — Orientador emite parecer
    # ------------------------------------------------------------------

    async def add_review(
        self,
        student_id: str,
        extension_id: str,
        parecer: str,
        orientador_uid: str,
    ) -> ExtensionResponse:
        """
        Atualiza o campo parecer_orientador de uma prorrogação pendente.
        Valida se o discente pertence ao orientador antes de persistir.
        """
        # Verifica se o discente tem este orientador
        student_snap = await self._student_ref(student_id).get()
        if not student_snap.exists:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Aluno não encontrado.")

        student_data: dict = student_snap.to_dict()
        if student_data.get("orientador_id") != orientador_uid:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Você não é o orientador deste discente.",
            )

        ext_ref = self._extensions_col(student_id).document(extension_id)
        ext_snap = await ext_ref.get()
        if not ext_snap.exists:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prorrogação não encontrada.")

        ext_data: dict = ext_snap.to_dict()
        if ext_data.get("status") != ExtensionStatus.PENDENTE.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Apenas prorrogações pendentes podem receber parecer.",
            )

        await ext_ref.update({"parecer_orientador": parecer})
        ext_data["parecer_orientador"] = parecer

        return _to_response(extension_id, ext_data)

    # ------------------------------------------------------------------
    # DECISION — Coordenação aprova ou rejeita (transação atômica)
    # ------------------------------------------------------------------

    async def process_decision(
        self,
        student_id: str,
        extension_id: str,
        payload: DecisionRequest,
        coordinator_uid: str,
    ) -> ExtensionResponse:
        """
        Processa a decisão da coordenação em uma transação Firestore:
        - Aprovação: atualiza extension + documento pai do aluno atomicamente.
        - Rejeição: apenas marca como rejeitada.
        """
        ext_ref    = self._extensions_col(student_id).document(extension_id)
        student_ref = self._student_ref(student_id)

        program_config = await self._get_program_config()
        duracao_meses: int = program_config.get("duracao_prorrogacao_meses", DEFAULT_DURACAO_MESES)

        @firestore.async_transactional
        async def _run_transaction(transaction: AsyncTransaction) -> dict:
            ext_snap     = await transaction.get(ext_ref)
            student_snap = await transaction.get(student_ref)

            if not ext_snap.exists:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prorrogação não encontrada.")
            if not student_snap.exists:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Aluno não encontrado.")

            ext_data:     dict = ext_snap.to_dict()
            student_data: dict = student_snap.to_dict()

            if ext_data.get("status") != ExtensionStatus.PENDENTE.value:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Apenas prorrogações pendentes podem ser deliberadas.",
                )

            now = datetime.now(tz=timezone.utc)

            if payload.aprovado:
                semestres: int = ext_data["semestres_solicitados"]
                delta          = _months_to_timedelta(semestres * duracao_meses)

                prazo_anterior: Optional[datetime] = student_data.get("prazo_final")
                if prazo_anterior is None:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="O aluno não possui prazo_final definido.",
                    )

                prazo_novo = prazo_anterior + delta

                # Atualiza a prorrogação
                ext_updates = {
                    "status":      ExtensionStatus.APROVADA.value,
                    "aprovado_por": coordinator_uid,
                    "aprovado_em":  now,
                    "prazo_novo":   prazo_novo,
                }
                # Atualiza o documento pai do aluno
                student_updates = {
                    "situacao_registrada": "em_prorrogacao",
                    "prazo_final":         prazo_novo,
                }

                transaction.update(ext_ref,     ext_updates)
                transaction.update(student_ref, student_updates)

                ext_data.update(ext_updates)

            else:
                ext_updates = {"status": ExtensionStatus.REJEITADA.value}
                transaction.update(ext_ref, ext_updates)
                ext_data.update(ext_updates)

            return ext_data

        transaction = self._db.transaction()
        final_data  = await _run_transaction(transaction)

        return _to_response(extension_id, final_data)

    # ------------------------------------------------------------------
    # LIST — Listagens por papel
    # ------------------------------------------------------------------

    async def list_by_student(self, student_id: str) -> list[ExtensionResponse]:
        """Lista todas as prorrogações de um aluno específico."""
        docs = [
            d async for d in self._extensions_col(student_id).order_by("criado_em", direction=firestore.Query.DESCENDING).stream()
        ]
        return [_to_response(d.id, d.to_dict()) for d in docs]

    async def list_pending_for_advisor(self, orientador_uid: str) -> list[ExtensionResponse]:
        """
        Lista prorrogações pendentes dos orientandos de um orientador.
        Busca alunos com orientador_id == orientador_uid e agrega pendentes.
        """
        students_query = (
            self._db.collection("students")
            .where("orientador_id", "==", orientador_uid)
        )
        results: list[ExtensionResponse] = []
        async for student_doc in students_query.stream():
            pending = (
                self._extensions_col(student_doc.id)
                .where("status", "==", ExtensionStatus.PENDENTE.value)
            )
            async for ext_doc in pending.stream():
                results.append(_to_response(ext_doc.id, ext_doc.to_dict()))
        return results

    async def list_all_pending(self) -> list[ExtensionResponse]:
        """
        Lista todas as prorrogações pendentes (visão da coordenação).
        Realiza collection group query na sub-coleção extensions.
        """
        query = (
            self._db.collection_group("extensions")
            .where("status", "==", ExtensionStatus.PENDENTE.value)
            .order_by("criado_em", direction=firestore.Query.ASCENDING)
        )
        return [_to_response(d.id, d.to_dict()) async for d in query.stream()]