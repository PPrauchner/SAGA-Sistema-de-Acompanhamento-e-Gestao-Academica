"""Servico agregador para a pagina unificada de Solicitacoes."""

from datetime import datetime, timezone
from typing import Any

from backend.app.core.auth import CurrentUser
from backend.app.models.request import RequestItem
from backend.app.repositories.activity_repository import ActivityRepository
from backend.app.repositories.advisor_repository import AdvisorRepository
from backend.app.repositories.coordination_transfer_repository import (
    CoordinationTransferRepository,
)
from backend.app.repositories.extension_repository import ExtensionRepository
from backend.app.repositories.firebase_repository import FirebaseRepository
from backend.app.repositories.student_repository import StudentRepository
from backend.app.repositories.transfer_repository import TransferRepository

# Origem de cada subtipo de Solicitação (CONTEXT.md → Solicitação): "formulario"
# nasce do formulário "Nova Solicitação"; "agregado" nasce de outro fluxo e é só
# consolidado nesta lista.
ORIGEM_POR_TIPO: dict[str, str] = {
    "atividade": "agregado",
    "producao": "agregado",
    "prorrogacao": "formulario",
    "trancamento": "formulario",
    "transferencia": "formulario",
    "transferencia_coordenacao": "agregado",
}


class RequestService:
    def __init__(self) -> None:
        self._activities = ActivityRepository()
        self._extensions = ExtensionRepository()
        self._transfers = TransferRepository()
        self._coord_transfers = CoordinationTransferRepository()
        self._students = StudentRepository()
        self._advisors = AdvisorRepository()
        self._users = FirebaseRepository("users")

    async def get_requests(self, user: CurrentUser) -> list[RequestItem]:
        """
        Retorna as requisições do usuário.

        Args:
            user: Usuário atual.

        Returns:
            List[RequestItem]: Lista de requisições do usuário.
        """
        requests: list[RequestItem] = []

        if user.role == "aluno":
            requests.extend(await self._get_student_requests(user))
        elif user.role == "orientador":
            requests.extend(await self._get_advisor_requests(user))
        elif user.role == "coordenacao":
            requests.extend(await self._get_coordinator_requests(user))
        elif user.role == "adm":
            requests.extend(await self._get_adm_requests())

        # Ordenar por data_solicitacao DESCENDENTE
        requests.sort(key=lambda req: req.data_solicitacao, reverse=True)
        return requests

    async def _get_student_requests(self, user: CurrentUser) -> list[RequestItem]:
        requests: list[RequestItem] = []
        students = await self._students.list_all()
        student = next((s for s in students if s.get("uid") == user.uid), None)
        if student is None:
            return requests

        student_id = student["id"]
        student_name = student.get("nome", "Desconhecido")

        activities = await self._activities.list_by_student(student_id)
        for activity in activities:
            if activity.get("status") == "enviado":
                requests.append(
                    self._build_request(
                        id=activity.get("id", ""),
                        tipo=self._activity_request_type(activity),
                        solicitante=student_name,
                        data=activity.get("criado_em")
                        or activity.get("data_realizacao")
                        or datetime.now(timezone.utc),
                        status=self._activity_status_for_student(activity),
                        payload=activity,
                    )
                )

        extensions = await self._extensions.list_by_student_ids({student_id})
        for ext in extensions:
            if ext.get("status") == "pendente":
                requests.append(
                    self._build_request(
                        id=ext.get("id", ""),
                        tipo=self._extension_request_type(ext),
                        solicitante=student_name,
                        data=ext.get("created_at")
                        or ext.get("solicitacao")
                        or datetime.now(timezone.utc),
                        status=ext.get("status", "pendente"),
                        payload=ext,
                    )
                )

        return requests

    async def _get_advisor_requests(self, user: CurrentUser) -> list[RequestItem]:
        """
        Retorna as requisições do orientador.

        Args:
            user: Usuário atual.

        Returns:
            List[RequestItem]: Lista de requisições do orientador.
        """
        requests: list[RequestItem] = []
        students = await self._get_advisor_students(user)
        student_ids = {s["id"] for s in students}
        student_names = {s["id"]: s.get("nome", "Desconhecido") for s in students}

        for sid in student_ids:
            activities = await self._activities.list_by_student(sid)
            for activity in activities:
                if activity.get("status") == "enviado" and not activity.get(
                    "parecer_orientador"
                ):
                    requests.append(
                        self._build_request(
                            id=activity.get("id", ""),
                            tipo=self._activity_request_type(activity),
                            solicitante=student_names.get(sid, "Desconhecido"),
                            data=activity.get("criado_em")
                            or datetime.now(timezone.utc),
                            status="pendente_parecer",
                            payload=activity,
                        )
                    )

        if student_ids:
            extensions = await self._extensions.list_by_student_ids(student_ids)
            for ext in extensions:
                if (
                    ext.get("status") == "pendente"
                    and not ext.get("parecer")
                    and not ext.get("parecer_orientador")
                ):
                    sid = ext.get("student_id")
                    requests.append(
                        self._build_request(
                            id=ext.get("id", ""),
                            tipo=self._extension_request_type(ext),
                            solicitante=student_names.get(
                                sid, ext.get("aluno_nome", "Desconhecido")
                            ),
                            data=ext.get("created_at")
                            or ext.get("solicitacao")
                            or datetime.now(timezone.utc),
                            status="pendente_parecer",
                            payload=ext,
                        )
                    )

        coord_transfers_as_successor = await self._coord_transfers.query(
            filters=[("successor_uid", "==", user.uid)]
        )
        coord_transfers_as_initiator = await self._coord_transfers.query(
            filters=[("initiator_uid", "==", user.uid)]
        )
        coord_transfers_map = {ct["id"]: ct for ct in coord_transfers_as_successor + coord_transfers_as_initiator}
        coord_transfers = [ct for ct in coord_transfers_map.values() if ct.get("status") in ["pendente", "concluido"]]
        for ct in coord_transfers:
            initiator_name = await self._get_user_name(ct.get("initiator_uid"))
            requests.append(
                self._build_request(
                    id=ct.get("id", ""),
                    tipo="transferencia_coordenacao",
                    solicitante=initiator_name,
                    data=ct.get("created_at") or datetime.now(timezone.utc),
                    status=ct.get("status", "pendente"),
                    payload=ct,
                )
            )

        return requests

    async def _get_coordinator_requests(self, user: CurrentUser) -> list[RequestItem]:
        """
        Retorna as requisições do coordenador.

        Args:
            user: Usuário atual.

        Returns:
            List[RequestItem]: Lista de requisições do coordenador.
        """
        requests: list[RequestItem] = []
        program_id = user.programa_id
        if not program_id:
            return []

        all_students = await self._students.list_all()
        program_students = {
            s["id"]: s for s in all_students if s.get("programa_id") == program_id
        }
        program_student_ids = set(program_students.keys())
        student_names = {
            s["id"]: s.get("nome", "Desconhecido") for s in program_students.values()
        }

        for sid in program_student_ids:
            activities = await self._activities.list_by_student(sid)
            for activity in activities:
                if activity.get("status") == "enviado" and activity.get(
                    "parecer_orientador"
                ):
                    requests.append(
                        self._build_request(
                            id=activity.get("id", ""),
                            tipo=self._activity_request_type(activity),
                            solicitante=student_names.get(sid, "Desconhecido"),
                            data=activity.get("criado_em")
                            or datetime.now(timezone.utc),
                            status="pendente_validacao",
                            payload=activity,
                        )
                    )

        extensions = await self._extensions.list_all()
        for ext in extensions:
            sid = ext.get("student_id")
            if (
                sid in program_student_ids
                and ext.get("status") == "pendente"
                and (ext.get("parecer") or ext.get("parecer_orientador"))
            ):
                requests.append(
                    self._build_request(
                        id=ext.get("id", ""),
                        tipo=self._extension_request_type(ext),
                        solicitante=student_names.get(
                            sid, ext.get("aluno_nome", "Desconhecido")
                        ),
                        data=ext.get("created_at")
                        or ext.get("solicitacao")
                        or datetime.now(timezone.utc),
                        status="pendente_aprovacao",
                        payload=ext,
                    )
                )

        transfers = await self._transfers.list_by_program(program_id)
        for t in transfers:
            if t.get("status") == "pendente":
                sid = t.get("student_id")
                student_name = student_names.get(
                    sid, t.get("aluno_nome", "Desconhecido")
                )
                requester_name = await self._get_advisor_name(t.get("solicitante_id"))
                label = f"{requester_name} (sobre {student_name})"
                requests.append(
                    self._build_request(
                        id=t.get("id", ""),
                        tipo="transferencia",
                        solicitante=label,
                        data=t.get("created_at") or datetime.now(timezone.utc),
                        status="pendente",
                        payload=t,
                    )
                )

        coord_transfers = await self._coord_transfers.list_by_program(program_id)
        for ct in coord_transfers:
            if (ct.get("initiator_uid") == user.uid or ct.get("successor_uid") == user.uid) and ct.get("status") in ["pendente", "concluido"]:
                successor_name = await self._get_user_name(ct.get("successor_uid"))
                requests.append(
                    self._build_request(
                        id=ct.get("id", ""),
                        tipo="transferencia_coordenacao",
                        solicitante=f"Para: {successor_name}",
                        data=ct.get("created_at") or datetime.now(timezone.utc),
                        status=ct.get("status", "pendente"),
                        payload=ct,
                    )
                )

        return requests

    async def _get_adm_requests(self) -> list[RequestItem]:
        """Retorna as transferências de coordenação pendentes de todos os programas.

        O papel `adm` é global (ADR-0001): gere coordenadores cross-programa e, por
        isso, enxerga as transferências de coordenação de qualquer programa — não
        apenas de um `programa_id`, que para o `adm` é `null`.

        Returns:
            Lista de RequestItem de `transferencia_coordenacao` com status pendente.
        """
        requests: list[RequestItem] = []
        all_coord_transfers = await self._coord_transfers.list_all()
        for ct in all_coord_transfers:
            if ct.get("status") == "pendente":
                initiator_name = await self._get_user_name(ct.get("initiator_uid"))
                requests.append(
                    self._build_request(
                        id=ct.get("id", ""),
                        tipo="transferencia_coordenacao",
                        solicitante=initiator_name,
                        data=ct.get("created_at") or datetime.now(timezone.utc),
                        status="pendente",
                        payload=ct,
                    )
                )
        return requests

    async def _get_advisor_students(self, user: CurrentUser) -> list[dict[str, Any]]:
        advisors = await self._advisors.list_all()
        advisor = next((item for item in advisors if item.get("uid") == user.uid), None)
        if not advisor:
            return []
        all_students = await self._students.list_all()
        return [s for s in all_students if s.get("orientador_id") == advisor["id"]]

    @staticmethod
    def _activity_request_type(activity: dict[str, Any]) -> str:
        return "producao" if activity.get("producao_id") else "atividade"

    @staticmethod
    def _extension_request_type(extension: dict[str, Any]) -> str:
        """
        Deriva o subtipo de Solicitação de um documento de `extensions/`.

        Args:
            extension: Documento de `extensions/` (campo `tipo`: `prazo_defesa`,
                `prazo_qualificacao`, `trancamento` ou `mudanca_nivel`).

        Returns:
            "trancamento" quando `extension.tipo == "trancamento"`, senão
            "prorrogacao" (demais subtipos de prazo).
        """
        return "trancamento" if extension.get("tipo") == "trancamento" else "prorrogacao"

    @staticmethod
    def _activity_status_for_student(activity: dict[str, Any]) -> str:
        if activity.get("parecer_orientador"):
            return "pendente_validacao"
        return "pendente_parecer"

    async def _get_user_name(self, uid: str | None) -> str:
        """
        Retorna o nome do usuário pelo ID.

        Args:
            uid: Id do usuário.

        Returns:
            Nome do usuário.
        """
        if not uid:
            return "Desconhecido"
        users = await self._users.list_all()
        user_record = next(
            (u for u in users if u.get("id") == uid or u.get("uid") == uid), None
        )
        return (
            user_record.get("nome", "Desconhecido") if user_record else "Desconhecido"
        )

    async def _get_advisor_name(self, advisor_id: str | None) -> str:
        """
        Retorna o nome do orientador pelo ID.

        Args:
            advisor_id: Id do orientador.

        Returns:
            Nome do orientador.
        """
        if not advisor_id:
            return "Desconhecido"
        advisor = await self._advisors.get(advisor_id)
        return advisor.get("nome", "Desconhecido") if advisor else "Desconhecido"

    def _build_request(
        self,
        id: str,
        tipo: Any,
        solicitante: str,
        data: Any,
        status: str,
        payload: dict,
    ) -> RequestItem:
        """
        Monta um objeto RequestItem com os dados da requisição.

        Args:
            id: Id da requisição.
            tipo: Tipo da requisição.
            solicitante: Nome do solicitante.
            data: Data da requisição.
            status: Status da requisição.
            payload: Payload original da requisição.

        Returns:
            RequestItem: Objeto RequestItem com os dados da requisição.
        """
        if not isinstance(data, datetime):
            data = datetime.now(timezone.utc)
        return RequestItem(
            id=id,
            tipo=tipo,
            origem=ORIGEM_POR_TIPO[tipo],
            solicitante_nome=solicitante,
            data_solicitacao=data,
            status=status,
            payload_original=payload,
        )
