"""
Serviço de gerenciamento do ciclo de vida das prorrogações de prazo.

Responsabilidades:
- Orquestrar solicitação (aluno), parecer (orientador) e decisão (coordenação),
  usando a coleção raiz `extensions/` (ADR-0006).
- Recalcular `students.prazo_final` na aprovação a partir da `nova_data` pedida
  pelo aluno (fluxo orientado a data — data-model §4), de forma idempotente.
- Respeitar `programs.max_prorrogacoes` (fonte canônica) no gate de limite.

Identidade dos parâmetros:
- `requester_uid`/`orientador_uid` são uids do Firebase Auth (de current_user.uid).
  O aluno é resolvido uid → doc id via StudentRepository; o orientador é resolvido
  uid → doc id via AdvisorRepository. `students.orientador_id` referencia o doc id
  de `advisors/` (não o uid).
- `process_decision` recebe o `CurrentUser` inteiro, e não só o uid: a deliberação
  é delimitada pelo `programa_id` da coordenação (tenant), além de registrar o uid
  em `aprovado_por`.
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import HTTPException, status

from backend.app.core.auth import CurrentUser
from backend.app.models.extension import (
    ApproveRequest,
    ExtensionCreateRequest,
    ExtensionDocument,
    ExtensionResponse,
    ExtensionStatus,
    ExtensionTipo,
    RejectRequest,
    ReviewRequest,
)
from backend.app.repositories.advisor_repository import AdvisorRepository
from backend.app.repositories.extension_repository import ExtensionRepository
from backend.app.repositories.program_repository import ProgramRepository
from backend.app.repositories.student_repository import StudentRepository

DEFAULT_MAX_PRORROGACOES = 1
DEFAULT_PROGRAMA_ID = "prog_default"
SITUACAO_EM_PRORROGACAO = "em_prorrogacao"

# Só a prorrogação de prazo coloca o aluno em `em_prorrogacao`; trancamento e
# mudança de nível são deferidos sem alterar a situação registrada (Spec 08).
TIPOS_DE_PRORROGACAO: frozenset[str] = frozenset(
    {ExtensionTipo.PRAZO_DEFESA.value, ExtensionTipo.PRAZO_QUALIFICACAO.value}
)


def _dump_for_firestore(doc: ExtensionDocument) -> dict:
    """Serializa o documento para o Firestore com enums como string."""
    data = doc.model_dump()
    for key in ("status", "tipo"):
        value = data.get(key)
        data[key] = getattr(value, "value", value)
    return data


def _to_response(data: dict, student: dict | None = None) -> ExtensionResponse:
    """Constrói a resposta pública a partir do documento (que já inclui `id`).

    Args:
        data: Documento da prorrogação, com o campo `id`.
        student: Aluno referenciado por `student_id`, quando disponível — usado
            para enriquecer a listagem com nome, matrícula e nível.

    Returns:
        A representação pública da prorrogação.
    """
    payload = dict(data)
    if student is not None:
        payload["student_nome"] = student.get("nome")
        payload["matricula"] = student.get("matricula")
        payload["nivel"] = student.get("nivel")
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

    async def _get_pending_extension(
        self,
        extension_id: str,
        coordinator: CurrentUser,
    ) -> dict:
        """Carrega a prorrogação e aplica os gates comuns à deliberação.

        Args:
            extension_id: Doc id da prorrogação.
            coordinator: Coordenação autenticada; `programa_id` delimita o
                tenant sobre o qual ela pode deliberar.

        Returns:
            O documento da prorrogação, garantidamente pendente e do programa
            da coordenação.

        Raises:
            HTTPException: 404 se não existir; 403 se for de outro programa;
                400 se não estiver pendente.
        """
        ext = await self._repo.get_extension(extension_id)
        if ext is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prorrogação não encontrada.")

        # Mesmo escopo de tenant de `list_for_user`: a coordenação só alcança o
        # próprio programa. `programa_id` nulo é o adm global (ADR-0001).
        if coordinator.programa_id and ext.get("programa_id") != coordinator.programa_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Você não pode deliberar prorrogações de outro programa.",
            )

        if ext.get("status") != ExtensionStatus.PENDENTE.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Apenas prorrogações pendentes podem ser deliberadas.",
            )
        return ext

    async def approve_extension(
        self,
        extension_id: str,
        payload: ApproveRequest,
        coordinator: CurrentUser,
    ) -> ExtensionResponse:
        """Aprova a prorrogação e recalcula o prazo do aluno (Spec 08).

        `students.prazo_final` recebe a `nova_data` solicitada — valor absoluto,
        portanto idempotente. `situacao_registrada` só passa a `em_prorrogacao`
        quando o tipo é de fato uma prorrogação de prazo; `trancamento` e
        `mudanca_nivel` não alteram a situação do aluno (Spec 08).

        Args:
            extension_id: Doc id da prorrogação.
            payload: Observação opcional da coordenação.
            coordinator: Coordenação autenticada.

        Returns:
            A prorrogação aprovada.

        Raises:
            HTTPException: 404 se a prorrogação/aluno não existir; 403 se for de
                outro programa; 400 se não estiver pendente.
        """
        ext = await self._get_pending_extension(extension_id, coordinator)

        student = await self._students.get(ext["student_id"])
        if student is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Aluno não encontrado.")

        nova_data = ext["nova_data"]
        student_updates: dict = {"prazo_final": nova_data}
        if ext.get("tipo") in TIPOS_DE_PRORROGACAO:
            student_updates["situacao_registrada"] = SITUACAO_EM_PRORROGACAO
        await self._students.update(ext["student_id"], student_updates)

        updates = {
            "status": ExtensionStatus.APROVADA.value,
            "prazo_novo": nova_data,
            "aprovado_por": coordinator.uid,
            "aprovado_em": datetime.now(tz=timezone.utc),
            "observacao_coordenacao": payload.observacao,
        }
        await self._repo.update_extension(extension_id, updates)
        return _to_response({**ext, **updates})

    async def reject_extension(
        self,
        extension_id: str,
        payload: RejectRequest,
        coordinator: CurrentUser,
    ) -> ExtensionResponse:
        """Rejeita a prorrogação, com motivo obrigatório (Spec 08).

        Não altera `prazo_final` nem `situacao_registrada` do aluno.

        Args:
            extension_id: Doc id da prorrogação.
            payload: Motivo da rejeição (obrigatório).
            coordinator: Coordenação autenticada.

        Returns:
            A prorrogação rejeitada.

        Raises:
            HTTPException: 404 se não existir; 403 se for de outro programa;
                400 se não estiver pendente.
        """
        ext = await self._get_pending_extension(extension_id, coordinator)

        updates = {
            "status": ExtensionStatus.REJEITADA.value,
            "motivo_rejeicao": payload.motivo,
            "rejeitado_por": coordinator.uid,
            "rejeitado_em": datetime.now(tz=timezone.utc),
        }
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
            student_by_id = {student["id"]: student}
        elif user.role == "orientador":
            advisor_id = await self._resolve_advisor_id(user.uid)
            if advisor_id is None:
                return []
            students = [
                s for s in await self._students.list_all()
                if s.get("orientador_id") == advisor_id
            ]
            student_by_id = {s["id"]: s for s in students}
            exts = [
                e for e in _sort_by_created_desc(await self._repo.list_all())
                if e.get("student_id") in student_by_id
            ]
        else:  # coordenação / adm
            student_by_id = {s["id"]: s for s in await self._students.list_all()}
            exts = _sort_by_created_desc(await self._repo.list_all())
            if user.programa_id:
                exts = [e for e in exts if e.get("programa_id") == user.programa_id]

        return [_to_response(e, student_by_id.get(e.get("student_id"))) for e in exts]
