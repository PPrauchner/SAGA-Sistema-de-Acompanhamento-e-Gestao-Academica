"""
Serviço de gerenciamento do ciclo de vida das prorrogações de prazo.

Responsabilidades:
- Orquestrar solicitação (aluno), parecer (orientador) e decisão (coordenação),
  usando a coleção raiz `extensions/` (ADR-0006).
- Recalcular `students.prazo_final` na aprovação a partir da `nova_data` pedida
  pelo aluno (fluxo orientado a data — data-model §4), de forma idempotente.
- Respeitar `programs.max_prorrogacoes` (fonte canônica) no gate de limite.

Identidade dos parâmetros:
- `requester_uid`/`orientador_uid`/`coordinator_uid` são uids do Firebase Auth
  (de current_user.uid). O aluno é resolvido uid → doc id via StudentRepository;
  o orientador é resolvido uid → doc id via AdvisorRepository. `students.orientador_id`
  referencia o doc id de `advisors/` (não o uid).
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum

from fastapi import HTTPException, status

from backend.app.core.auth import CurrentUser
from backend.app.models.extension import (
    DecisionRequest,
    ExtensionCreateRequest,
    ExtensionDocument,
    ExtensionResponse,
    ExtensionStatus,
    ReviewRequest,
)
from backend.app.repositories.advisor_repository import AdvisorRepository
from backend.app.repositories.extension_repository import ExtensionRepository
from backend.app.repositories.program_repository import ProgramRepository
from backend.app.repositories.student_repository import StudentRepository

DEFAULT_MAX_PRORROGACOES = 1
DEFAULT_PROGRAMA_ID = "prog_default"
SITUACAO_EM_PRORROGACAO = "em_prorrogacao"


def _dump_for_firestore(doc: ExtensionDocument) -> dict:
    """Serializa o documento para o Firestore com enums como string."""
    data = doc.model_dump()
    for key in ("status", "tipo"):
        value = data.get(key)
        data[key] = getattr(value, "value", value)
    return data


def _to_response(data: dict, student_nome: str | None = None) -> ExtensionResponse:
    """Constrói a resposta pública a partir do documento (que já inclui `id`)."""
    payload = dict(data)
    if student_nome is not None:
        payload["student_nome"] = student_nome
    return ExtensionResponse(**payload)


def _sort_by_created_desc(items: list[dict]) -> list[dict]:
    """Ordena por created_at desc em memória."""
    return sorted(items, key=lambda d: d.get("created_at") or "", reverse=True)


class ExtensionService:
    """Serviço do ciclo de vida das prorrogações de prazo."""

    def __init__(
        self,
        repository: ExtensionRepository | None = None,
        students: StudentRepository | None = None,
        advisors: AdvisorRepository | None = None,
        programs: ProgramRepository | None = None,
    ) -> None:
        self._repo = repository or ExtensionRepository()
        self._students = students or StudentRepository()
        self._advisors = advisors or AdvisorRepository()
        self._programs = programs or ProgramRepository()

    # ------------------------------------------------------------------
    # Helpers internos
    # ------------------------------------------------------------------

    async def _resolve_advisor_id(self, uid: str) -> str | None:
        """Resolve uid → doc id de `advisors/` (None se o usuário não orienta)."""
        results = await self._advisors.query(filters=[("uid", "==", uid)], limit=1)
        return results[0]["id"] if results else None

    async def _max_prorrogacoes(self, programa_id: str | None) -> int:
        """Lê `max_prorrogacoes` do programa (fonte canônica), default 1."""
        program = await self._programs.get_config(programa_id or DEFAULT_PROGRAMA_ID)
        if not program:
            return DEFAULT_MAX_PRORROGACOES
        return program.get("max_prorrogacoes", DEFAULT_MAX_PRORROGACOES)

    # ------------------------------------------------------------------
    # Casos de uso
    # ------------------------------------------------------------------

    async def create_extension(
        self,
        payload: ExtensionCreateRequest,
        requester_uid: str,
    ) -> ExtensionResponse:
        """Cria uma solicitação de prorrogação (status 'pendente') para o aluno.

        Args:
            payload: Dados da solicitação (tipo, motivo, plano, nova_data).
            requester_uid: uid do aluno autenticado.

        Returns:
            A prorrogação criada.

        Raises:
            HTTPException: 404 se o aluno não existir; 409 se já houver
                solicitação pendente ou o limite de prorrogações for atingido.
        """
        student = await self._students.get_by_uid(requester_uid)
        if student is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Aluno não encontrado.")

        student_id = student["id"]
        programa_id = student.get("programa_id")

        if await self._repo.has_pending(student_id):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Já existe uma solicitação de prorrogação pendente.",
            )

        max_allowed = await self._max_prorrogacoes(programa_id)
        if await self._repo.count_approved(student_id) >= max_allowed:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Limite de {max_allowed} prorrogação(ões) aprovada(s) já atingido.",
            )

        doc = ExtensionDocument(
            student_id=student_id,
            requester_id=requester_uid,
            programa_id=programa_id,
            tipo=payload.tipo,
            motivo=payload.motivo,
            plano_atualizado=payload.plano_atualizado,
            status=ExtensionStatus.PENDENTE,
            nova_data=payload.nova_data,
            data_atual=student.get("prazo_final"),
            created_at=datetime.now(tz=timezone.utc),
        )
        data = _dump_for_firestore(doc)
        new_id = await self._repo.create_extension(data)
        return _to_response({**data, "id": new_id})

    async def add_review(
        self,
        extension_id: str,
        payload: ReviewRequest,
        orientador_uid: str,
    ) -> ExtensionResponse:
        """Registra o parecer do orientador (campo, não muda o status).

        Args:
            extension_id: Doc id da prorrogação.
            payload: Parecer técnico do orientador.
            orientador_uid: uid do orientador autenticado.

        Returns:
            A prorrogação com o parecer registrado.

        Raises:
            HTTPException: 404 se a prorrogação/aluno não existir; 403 se o
                usuário não for o orientador do aluno; 400 se não estiver pendente.
        """
        ext = await self._repo.get_extension(extension_id)
        if ext is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prorrogação não encontrada.")
        if ext.get("status") != ExtensionStatus.PENDENTE.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Apenas prorrogações pendentes podem receber parecer.",
            )

        student = await self._students.get(ext["student_id"])
        if student is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Aluno não encontrado.")

        advisor_id = await self._resolve_advisor_id(orientador_uid)
        if advisor_id is None or student.get("orientador_id") != advisor_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Você não é o orientador deste discente.",
            )

        await self._repo.update_extension(extension_id, {"parecer_orientador": payload.parecer_orientador})
        return _to_response({**ext, "parecer_orientador": payload.parecer_orientador})

    async def process_decision(
        self,
        extension_id: str,
        payload: DecisionRequest,
        coordinator_uid: str,
    ) -> ExtensionResponse:
        """Homologa a decisão da coordenação (aprovar/rejeitar).

        Na aprovação, recalcula `students.prazo_final` = `nova_data` solicitada
        (idempotente, pois é valor absoluto) e marca o aluno em prorrogação.

        Args:
            extension_id: Doc id da prorrogação.
            payload: Decisão (aprovar/rejeitar).
            coordinator_uid: uid da coordenação.

        Returns:
            A prorrogação deliberada (aprovada ou rejeitada).

        Raises:
            HTTPException: 404 se a prorrogação/aluno não existir; 400 se não
                estiver pendente.
        """
        ext = await self._repo.get_extension(extension_id)
        if ext is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prorrogação não encontrada.")
        if ext.get("status") != ExtensionStatus.PENDENTE.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Apenas prorrogações pendentes podem ser deliberadas.",
            )

        student = await self._students.get(ext["student_id"])
        if student is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Aluno não encontrado.")

        now = datetime.now(tz=timezone.utc)

        if payload.acao == "aprovar":
            nova_data = ext["nova_data"]
            # Idempotente: prazo_final absoluto (= nova_data), não incremental.
            await self._students.update(
                ext["student_id"],
                {"prazo_final": nova_data, "situacao_registrada": SITUACAO_EM_PRORROGACAO},
            )
            updates = {
                "status": ExtensionStatus.APROVADA.value,
                "prazo_novo": nova_data,
                "aprovado_por": coordinator_uid,
                "aprovado_em": now,
            }
        else:
            updates = {"status": ExtensionStatus.REJEITADA.value}

        await self._repo.update_extension(extension_id, updates)
        return _to_response({**ext, **updates})

    async def list_for_user(self, user: CurrentUser) -> list[ExtensionResponse]:
        """Lista prorrogações conforme o papel (Spec 08 — GET /extensions).

        Aluno vê as próprias; orientador vê as dos seus orientandos; coordenação
        vê todas do seu programa. Cada item é enriquecido com o nome do aluno.
        """
        if user.role == "aluno":
            student = await self._students.get_by_uid(user.uid)
            if student is None:
                return []
            exts = await self._repo.list_by_student(student["id"])
            nome_by_id = {student["id"]: student.get("nome")}
        elif user.role == "orientador":
            advisor_id = await self._resolve_advisor_id(user.uid)
            if advisor_id is None:
                return []
            students = [
                s for s in await self._students.list_all()
                if s.get("orientador_id") == advisor_id
            ]
            nome_by_id = {s["id"]: s.get("nome") for s in students}
            exts = [
                e for e in _sort_by_created_desc(await self._repo.list_all())
                if e.get("student_id") in nome_by_id
            ]
        else:  # coordenação / adm
            nome_by_id = {s["id"]: s.get("nome") for s in await self._students.list_all()}
            exts = _sort_by_created_desc(await self._repo.list_all())
            if user.programa_id:
                exts = [e for e in exts if e.get("programa_id") == user.programa_id]

        return [_to_response(e, nome_by_id.get(e.get("student_id"))) for e in exts]
