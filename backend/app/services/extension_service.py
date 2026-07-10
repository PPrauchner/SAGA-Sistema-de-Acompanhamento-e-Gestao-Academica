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

    async def list_pending_for_coordination(
        self,
        user: CurrentUser,
        status: str = STATUS_PENDING,
    ) -> list[dict[str, Any]]:
        """Lista as prorrogações do programa da coordenação para a fila de aprovação.

        Args:
            user: Coordenação autenticada; `programa_id` delimita o escopo (tenant).
            status: Status a filtrar (default 'pendente').

        Returns:
            Prorrogações do programa com o status indicado, normalizadas (nome e nível do
            aluno resolvidos), prontas para a seção de prorrogações do CoordDashboard.
        """
        extensions = await self._repo.list_by_program(user.programa_id, status)
        students = await self._students.list_by_program(user.programa_id)
        students_by_id = {student["id"]: student for student in students}
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

    async def approve_extension(
        self,
        extension_id: str,
        user: CurrentUser,
    ) -> dict[str, Any]:
        """Aprova uma solicitação de prorrogação/trancamento pendente.

        Recalcula o `prazo_final` do aluno para a `nova_data` solicitada,
        escrevendo através do `StudentRepository` — o mesmo caminho de
        atualização já usado pelo cadastro de aluno e pela transferência de
        orientando — em vez de duplicar a lógica de escrita. Quando a
        solicitação não traz `nova_data` (permitido para `trancamento`, ver
        `ExtensionCreateRequest`), o `prazo_final` é **preservado** em vez de
        ser sobrescrito com `None`, evitando apagar o prazo do aluno.

        Args:
            extension_id: Id do documento em `extensions/`.
            user: Coordenação autenticada; `programa_id` delimita o escopo.

        Returns:
            A solicitação normalizada com `status="aprovada"`.

        Raises:
            HTTPException: 404 se não encontrada, 400 se não estiver
                pendente, 403 se pertencer a outro programa.
        """
        extension = await self._get_pending_extension(extension_id, user)

        now = datetime.now(timezone.utc)
        student_id = extension.get("student_id")
        nova_data = extension.get("nova_data") or extension.get("prazo_novo")
        if nova_data is not None:
            await self._students.update(student_id, {"prazo_final": nova_data})
        await self._repo.update(
            extension_id,
            {
                "status": "aprovada",
                "aprovado_por": user.uid,
                "aprovado_em": now,
            },
        )

        student = await self._find_student(student_id)
        return self._normalize_response(
            {
                **extension,
                "status": "aprovada",
                "aprovado_por": user.uid,
                "aprovado_em": now,
            },
            student,
        )

    async def reject_extension(
        self,
        extension_id: str,
        motivo: str,
        user: CurrentUser,
    ) -> dict[str, Any]:
        """Rejeita uma solicitação de prorrogação/trancamento pendente.

        Args:
            extension_id: Id do documento em `extensions/`.
            motivo: Justificativa da rejeição (obrigatória).
            user: Coordenação autenticada; `programa_id` delimita o escopo.

        Returns:
            A solicitação normalizada com `status="rejeitada"`.

        Raises:
            HTTPException: 422 se `motivo` vier vazio, 404 se não encontrada,
                400 se não estiver pendente, 403 se de outro programa.
        """
        if not motivo.strip():
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Motivo e obrigatorio para rejeitar a solicitacao",
            )

        extension = await self._get_pending_extension(extension_id, user)

        now = datetime.now(timezone.utc)
        await self._repo.update(
            extension_id,
            {
                "status": "rejeitada",
                "motivo_rejeicao": motivo,
                "rejeitado_por": user.uid,
                "rejeitado_em": now,
            },
        )

        student = await self._find_student(extension.get("student_id"))
        return self._normalize_response(
            {
                **extension,
                "status": "rejeitada",
                "motivo_rejeicao": motivo,
                "rejeitado_por": user.uid,
                "rejeitado_em": now,
            },
            student,
        )

    async def _get_pending_extension(
        self,
        extension_id: str,
        user: CurrentUser,
    ) -> dict[str, Any]:
        extension = await self._repo.get(extension_id)
        if extension is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Solicitacao de prorrogacao nao encontrada",
            )
        if extension.get("status") != STATUS_PENDING:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Solicitacao precisa estar pendente para esta decisao",
            )
        if user.programa_id and user.programa_id != extension.get("programa_id"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Coordenacao nao pode decidir solicitacao de outro programa",
            )
        return extension

    async def _find_student(self, student_id: str | None) -> dict[str, Any] | None:
        if not student_id:
            return None
        return await self._students.get(student_id)

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
                "aluno_uid": student.get("uid") if student else result.get("aluno_uid"),
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
