"""
Serviço de leitura dos logs de auditoria (aspecto A02).

Responsabilidades:
- list_audit_logs(): lê a coleção audit_logs/, aplica filtros opcionais (usuario_id,
  operacao, modulo, resultado_status, data_inicio, data_fim), ordena do mais recente ao
  mais antigo e devolve uma página (AuditLogPage) com base em page/page_size.
- Escopa por papel: a coordenação enxerga todos os logs; o orientador enxerga apenas os
  logs cujo `usuario_id` (ator da operação) é um dos seus orientandos — i.e., ações
  executadas pelos próprios orientandos (resolução advisors→students).
- Resolve `usuario_id`→`usuario_nome` na página retornada (read path), via UserNameResolver;
  o `usuario_id` persistido permanece a chave canônica.
- Não escreve em audit_logs/ — a escrita é exclusiva do aspecto @audit_operation.
- A paginação e os filtros são aplicados em memória: a coleção é apenas anexada (nunca
  deletada) e, no MVP single-tenant, o volume é compatível com leitura completa.
"""

from __future__ import annotations

from datetime import datetime, timezone

from backend.app.core.auth import CurrentUser
from backend.app.models.audit import AuditLogPage, AuditLogResponse
from backend.app.repositories.advisor_repository import AdvisorRepository
from backend.app.repositories.firebase_repository import FirebaseRepository
from backend.app.repositories.student_repository import StudentRepository
from backend.app.services.user_name_resolver import UserNameResolver

_MIN_TIMESTAMP = datetime.min.replace(tzinfo=timezone.utc)


class AuditService:
    """Serviço de consulta dos logs de auditoria gerados pelo aspecto A02."""

    def __init__(
        self,
        advisors: AdvisorRepository | None = None,
        students: StudentRepository | None = None,
        names: UserNameResolver | None = None,
    ) -> None:
        self._repo = FirebaseRepository("audit_logs")
        # Resolvem o escopo do orientador (advisors→students). Injetáveis para teste; só
        # são consultados quando o papel é 'orientador', então a construção não faz I/O.
        self._advisors = advisors or AdvisorRepository()
        self._students = students or StudentRepository()
        # Resolve usuario_id→nome apenas para a página retornada (read path). O repo de
        # users é construído aqui (não dentro do resolver) para reaproveitar o mesmo
        # FirebaseRepository do módulo, mantendo a injeção/monkeypatch consistente.
        self._names = names or UserNameResolver(FirebaseRepository("users"))

    @staticmethod
    def _matches(
        log: dict,
        *,
        usuario_id: str | None,
        operacao: str | None,
        modulo: str | None,
        resultado_status: str | None,
        data_inicio: datetime | None,
        data_fim: datetime | None,
    ) -> bool:
        if usuario_id and log.get("usuario_id") != usuario_id:
            return False
        if operacao and log.get("operacao") != operacao:
            return False
        if modulo and log.get("modulo") != modulo:
            return False
        if resultado_status and log.get("resultado_status") != resultado_status:
            return False

        timestamp = log.get("timestamp")
        if (data_inicio or data_fim) and timestamp is None:
            return False
        if data_inicio and timestamp < data_inicio:
            return False
        if data_fim and timestamp > data_fim:
            return False

        return True

    async def _allowed_usuario_ids(self, user: CurrentUser | None) -> set[str] | None:
        """Resolve os `usuario_id` que o usuário pode enxergar, conforme o papel.

        Args:
            user: Usuário autenticado, ou None para consulta irrestrita.

        Returns:
            None quando o acesso é irrestrito (coordenação ou sem usuário). Para o
            orientador, o conjunto de uids dos seus orientandos (ações executadas por
            eles); conjunto vazio se o orientador não tiver doc em advisors/.
        """
        if user is None or user.role != "orientador":
            return None

        advisors = await self._advisors.list_all()
        advisor = next((item for item in advisors if item.get("uid") == user.uid), None)
        if advisor is None:
            return set()

        students = await self._students.list_all()
        return {
            student["uid"]
            for student in students
            if student.get("orientador_id") == advisor["id"] and student.get("uid")
        }

    async def list_audit_logs(
        self,
        *,
        usuario_id: str | None = None,
        operacao: str | None = None,
        modulo: str | None = None,
        resultado_status: str | None = None,
        data_inicio: datetime | None = None,
        data_fim: datetime | None = None,
        page: int = 1,
        page_size: int = 20,
        user: CurrentUser | None = None,
    ) -> AuditLogPage:
        logs = await self._repo.list_all()
        allowed_usuario_ids = await self._allowed_usuario_ids(user)

        filtered = [
            log
            for log in logs
            if self._matches(
                log,
                usuario_id=usuario_id,
                operacao=operacao,
                modulo=modulo,
                resultado_status=resultado_status,
                data_inicio=data_inicio,
                data_fim=data_fim,
            )
            and (allowed_usuario_ids is None or log.get("usuario_id") in allowed_usuario_ids)
        ]

        filtered.sort(
            key=lambda log: log.get("timestamp") or _MIN_TIMESTAMP,
            reverse=True,
        )

        start = (page - 1) * page_size
        window = filtered[start : start + page_size]

        nomes = await self._names.resolve(log.get("usuario_id") for log in window)

        return AuditLogPage(
            items=[
                AuditLogResponse.model_validate(
                    {**log, "usuario_nome": nomes.get(log.get("usuario_id"))}
                )
                for log in window
            ],
            page=page,
            page_size=page_size,
            total=len(filtered),
        )
