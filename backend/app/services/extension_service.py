<<<<<<< HEAD
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
        advisor_doc_id = await self._repo.get_advisor_doc_id_by_uid(orientador_uid)
        if student_data.get("orientador_id") != advisor_doc_id:
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
        
        results: list[ExtensionResponse] = []
        async for student_doc in students_query.stream():
           advisor_doc_id = await self._repo.get_advisor_doc_id_by_uid(orientador_uid)
           students_query = (
                self._repo._db.collection("students")
                .where("orientador_id", "==", advisor_doc_id)
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
=======
"""Servico de negocio para solicitacoes de prorrogacao."""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any

from fastapi import HTTPException, status

from backend.app.core.auth import CurrentUser
from backend.app.models.extension import ExtensionCreateRequest
from backend.app.repositories.advisor_repository import AdvisorRepository
from backend.app.repositories.extension_repository import (
    STATUS_PENDING,
    ExtensionRepository,
)
from backend.app.repositories.student_repository import StudentRepository


def _to_date(value: object) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value[:10])
        except ValueError:
            return None
    return None


class ExtensionService:
    def __init__(
        self,
        repo: ExtensionRepository | None = None,
        student_repo: StudentRepository | None = None,
        advisor_repo: AdvisorRepository | None = None,
    ) -> None:
        self._repo = repo or ExtensionRepository()
        self._students = student_repo or StudentRepository()
        self._advisors = advisor_repo or AdvisorRepository()

    async def list_extensions(self, user: CurrentUser) -> list[dict[str, Any]]:
        visible_students = await self._visible_students(user)
        visible_ids = {student["id"] for student in visible_students}
        students_by_id = {student["id"]: student for student in visible_students}

        if user.role == "coordenacao":
            extensions = await self._repo.list_all()
            all_students = await self._students.list_all()
            students_by_id = {student["id"]: student for student in all_students}
        else:
            extensions = await self._repo.list_by_student_ids(visible_ids)

        return [
            self._normalize_response(extension, students_by_id.get(extension.get("student_id")))
            for extension in extensions
        ]

    async def create_extension(
        self,
        data: ExtensionCreateRequest,
        user: CurrentUser,
    ) -> dict[str, Any]:
        student = await self._resolve_target_student(data.student_id, user)
        student_id = student["id"]

        if await self._repo.has_pending_for_student(student_id):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Ja existe solicitacao de prorrogacao pendente para este aluno",
            )

        now = datetime.now(timezone.utc)
        prazo_atual = _to_date(student.get("prazo_final"))
        payload = {
            "tipo": data.tipo,
            "status": STATUS_PENDING,
            "student_id": student_id,
            "motivo": data.motivo.strip(),
            "nova_data": data.nova_data,
            "prazo_novo": data.nova_data,
            "data_atual": prazo_atual,
            "prazo_atual": prazo_atual,
            "created_at": now,
            "solicitacao": now,
            "requester_id": user.uid,
            "programa_id": student.get("programa_id"),
        }
        extension_id = await self._repo.create(payload)
        return self._normalize_response({"id": extension_id, **payload}, student)

    async def _visible_students(self, user: CurrentUser) -> list[dict[str, Any]]:
        students = await self._students.list_all()

        if user.role == "coordenacao":
            return students

        if user.role == "aluno":
            return [student for student in students if student.get("uid") == user.uid]

        advisor_id = await self._advisor_id_for_user(user)
        if advisor_id is None:
            return []
        return [
            student
            for student in students
            if student.get("orientador_id") == advisor_id
        ]

    async def _resolve_target_student(
        self,
        requested_student_id: str | None,
        user: CurrentUser,
    ) -> dict[str, Any]:
        visible_students = await self._visible_students(user)

        if user.role == "aluno":
            if not visible_students:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Aluno nao encontrado para o usuario autenticado",
                )
            return visible_students[0]

        if user.role == "orientador":
            if not requested_student_id:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="student_id e obrigatorio para orientador",
                )
            student = next(
                (
                    item
                    for item in visible_students
                    if item.get("id") == requested_student_id
                ),
                None,
            )
            if student is None:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Orientador so pode solicitar para seus orientandos",
                )
            return student

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Coordenacao nao pode criar solicitacao de prorrogacao",
        )

    async def _advisor_id_for_user(self, user: CurrentUser) -> str | None:
        advisors = await self._advisors.list_all()
        advisor = next((item for item in advisors if item.get("uid") == user.uid), None)
        return advisor.get("id") if advisor else None

    @staticmethod
    def _normalize_response(
        extension: dict[str, Any],
        student: dict[str, Any] | None,
    ) -> dict[str, Any]:
        result = dict(extension)
        student_id = result.get("student_id") or ""
        aluno_nome = student.get("nome", "") if student else result.get("aluno_nome", "")
        nova_data = _to_date(result.get("nova_data") or result.get("prazo_novo"))
        prazo_atual = _to_date(result.get("data_atual") or result.get("prazo_atual"))
        created_at = result.get("created_at") or result.get("solicitacao")
        if not isinstance(created_at, datetime):
            created_at = datetime.now(timezone.utc)

        result.update(
            {
                "student_id": student_id,
                "aluno_id": student_id,
                "aluno_nome": aluno_nome,
                "aluno": aluno_nome,
                "matricula": student.get("matricula") if student else result.get("matricula"),
                "nivel": student.get("nivel") if student else result.get("nivel"),
                "nova_data": nova_data,
                "prazo_novo": nova_data,
                "data_atual": prazo_atual,
                "prazo_atual": prazo_atual,
                "created_at": created_at,
                "solicitacao": created_at,
                "justificativa": result.get("motivo", ""),
                "parecer": result.get("parecer") or result.get("parecer_orientador"),
            }
        )
        return result
>>>>>>> 0161ba8854c4238232217a8a4715b9d5484d34b9
