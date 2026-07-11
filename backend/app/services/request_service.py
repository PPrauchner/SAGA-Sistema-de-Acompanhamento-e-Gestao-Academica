"""Servico agregador para a pagina unificada de Solicitacoes."""

import asyncio
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
        students = await self._students.query(filters=[("uid", "==", user.uid)])
        student = students[0] if students else None
        if student is None:
            return requests

        student_id = student["id"]
        student_name = student.get("nome", "Desconhecido")

        # Atividades e prorrogações são independentes — busca em paralelo (issue #319).
        activities, extensions = await asyncio.gather(
            self._activities.list_by_student(student_id),
            self._extensions.list_by_student_ids({student_id}),
        )
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

        # As quatro fontes são independentes: a lista agregada de atividades substitui
        # o loop N×list_by_student e tudo é buscado em paralelo (issue #319).
        (
            all_activities,
            extensions,
            coord_transfers_as_successor,
            coord_transfers_as_initiator,
        ) = await asyncio.gather(
            self._activities.list_all_grouped(),
            self._extensions.list_by_student_ids(student_ids),
            self._coord_transfers.query(filters=[("successor_uid", "==", user.uid)]),
            self._coord_transfers.query(filters=[("initiator_uid", "==", user.uid)]),
        )

        for activity in all_activities:
            sid = activity.get("student_id")
            if sid not in student_ids:
                continue
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

        coord_transfers_map = {ct["id"]: ct for ct in coord_transfers_as_successor + coord_transfers_as_initiator}
        coord_transfers = [ct for ct in coord_transfers_map.values() if ct.get("status") in ["pendente", "concluido"]]
        initiator_names = await asyncio.gather(
            *(self._get_user_name(ct.get("initiator_uid")) for ct in coord_transfers)
        )
        for ct, initiator_name in zip(coord_transfers, initiator_names):
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

        # As cinco fontes são independentes: a lista agregada de atividades substitui
        # o loop N×list_by_student e tudo é buscado em paralelo (issue #319).
        (
            all_students,
            all_activities,
            extensions,
            transfers,
            coord_transfers,
        ) = await asyncio.gather(
            self._students.list_all(),
            self._activities.list_all_grouped(),
            self._extensions.list_all(),
            self._transfers.list_by_program(program_id),
            self._coord_transfers.list_by_program(program_id),
        )
        program_students = {
            s["id"]: s for s in all_students if s.get("programa_id") == program_id
        }
        program_student_ids = set(program_students.keys())
        student_names = {
            s["id"]: s.get("nome", "Desconhecido") for s in program_students.values()
        }

        for activity in all_activities:
            sid = activity.get("student_id")
            if sid not in program_student_ids:
                continue
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

        pending_transfers = [t for t in transfers if t.get("status") == "pendente"]
        requester_names = await asyncio.gather(
            *(self._get_advisor_name(t.get("solicitante_id")) for t in pending_transfers)
        )
        for t, requester_name in zip(pending_transfers, requester_names):
            sid = t.get("student_id")
            student_name = student_names.get(
                sid, t.get("aluno_nome", "Desconhecido")
            )
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

        own_coord_transfers = [
            ct
            for ct in coord_transfers
            if (ct.get("initiator_uid") == user.uid or ct.get("successor_uid") == user.uid)
            and ct.get("status") in ["pendente", "concluido"]
        ]
        successor_names = await asyncio.gather(
            *(self._get_user_name(ct.get("successor_uid")) for ct in own_coord_transfers)
        )
        for ct, successor_name in zip(own_coord_transfers, successor_names):
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
        """Adm global vê as transferências de coordenação de todos os programas."""
        requests: list[RequestItem] = []
        coord_transfers = await self._coord_transfers.list_all()
        relevant = [
            ct for ct in coord_transfers if ct.get("status") in ["pendente", "concluido"]
        ]
        initiator_names = await asyncio.gather(
            *(self._get_user_name(ct.get("initiator_uid")) for ct in relevant)
        )
        for ct, initiator_name in zip(relevant, initiator_names):
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

    async def _get_advisor_students(self, user: CurrentUser) -> list[dict[str, Any]]:
        advisors = await self._advisors.query(filters=[("uid", "==", user.uid)])
        advisor = advisors[0] if advisors else None
        if not advisor:
            return []
        return await self._students.query(
            filters=[("orientador_id", "==", advisor["id"])]
        )

    @staticmethod
    def _activity_request_type(activity: dict[str, Any]) -> str:
        return "producao" if activity.get("producao_id") else "atividade"

    @staticmethod
    def _extension_request_type(extension: dict[str, Any]) -> str:
        """Mapeia extensions.tipo para o tipo exibido na Caixa de Entrada unificada.

        Preserva os subtipos de prorrogação (prazo_defesa/prazo_qualificacao)
        distintos da prorrogação genérica — antes todos colapsavam em
        "prorrogacao" (issue #298). "mudanca_nivel" (escopo futuro, fora do MVP)
        cai no fallback "prorrogacao".
        """
        tipo = extension.get("tipo")
        if tipo == "trancamento":
            return "trancamento"
        if tipo in ("prazo_defesa", "prazo_qualificacao"):
            return tipo
        return "prorrogacao"

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
        # users/ é chaveado pelo uid — leitura direta em vez de list_all + busca linear.
        user_record = await self._users.get(uid)
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
            solicitante_nome=solicitante,
            data_solicitacao=data,
            status=status,
            payload_original=payload,
        )
