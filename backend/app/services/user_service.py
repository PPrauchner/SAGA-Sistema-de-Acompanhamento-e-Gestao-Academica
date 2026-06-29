"""
Serviço de gestão de usuários privilegiados.

Responsabilidades:
- create_coordinator: adm cria um coordenador diretamente (sem fluxo de
  convite), definindo e-mail, senha, nome e programa no Firebase Auth e
  Firestore. Rejeita e-mail que já possui conta ativa (409).
- update_profile: usuário autenticado edita o próprio perfil (nome para todos
  os papéis; departamento apenas para orientador, gravado no documento
  advisors vinculado). Remove o campo telefone do documento se existir.

Referência: docs/specs/04_autenticacao.json; issues #162 (US-PA05), #195.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException, status
from firebase_admin import auth as firebase_auth
from firebase_admin import firestore

from backend.app.core.auth import CurrentUser
from backend.app.core.firebase import get_auth_client
from backend.app.models.user import (
    CreateCoordinatorRequest,
    CreateCoordinatorResponse,
    ProfileUpdateRequest,
    ProfileUpdateResponse,
)
from backend.app.repositories.advisor_repository import AdvisorRepository
from backend.app.repositories.firebase_repository import FirebaseRepository


class UserService:
    """Orquestra operações de criação de usuários privilegiados (coordenadores).

    Attributes:
        _users: Repositório Firestore da coleção users.
        _auth: Cliente Firebase Auth (Admin SDK).
    """

    def __init__(
        self,
        user_repo: FirebaseRepository | None = None,
        auth_client: Any | None = None,
        advisor_repo: FirebaseRepository | None = None,
    ) -> None:
        self._users = user_repo or FirebaseRepository("users")
        self._auth = auth_client if auth_client is not None else get_auth_client()
        self._advisors = advisor_repo or AdvisorRepository()

    async def create_coordinator(
        self, data: CreateCoordinatorRequest
    ) -> CreateCoordinatorResponse:
        """Cria um coordenador no Firebase Auth e no Firestore.

        Args:
            data: E-mail, nome, senha e programa_id do novo coordenador.

        Returns:
            CreateCoordinatorResponse com uid e e-mail da conta criada.

        Raises:
            HTTPException: 409 se o e-mail já possui conta ativa.
        """
        if self._email_ja_tem_conta(data.email):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="E-mail já possui conta ativa",
            )

        user_record = self._auth.create_user(email=data.email, password=data.senha)
        uid = user_record.uid

        claims = {"role": "coordenacao", "programa_id": data.programa_id}
        self._auth.set_custom_user_claims(uid, claims)

        agora = datetime.now(timezone.utc)
        await self._users.set(uid, {
            "uid": uid,
            "email": data.email,
            "nome": data.nome,
            "role": "coordenacao",
            "programa_id": data.programa_id,
            "ativo": True,
            "primeiro_acesso_completo": True,
            "criado_em": agora,
            "atualizado_em": agora,
        })

        return CreateCoordinatorResponse(
            message=f"Coordenador {data.email} criado com sucesso",
            uid=uid,
            email=data.email,
        )

    async def update_profile(
        self, data: ProfileUpdateRequest, user: CurrentUser
    ) -> ProfileUpdateResponse:
        """Atualiza o próprio perfil do usuário autenticado.

        Grava `nome` em users/{uid} para qualquer papel e remove o campo
        `telefone` do documento caso exista. `departamento` é aceito apenas
        para orientador e gravado no documento advisors vinculado.

        Args:
            data: Campos editáveis do perfil (nome e, opcionalmente, departamento).
            user: Identidade autenticada extraída do JWT.

        Returns:
            ProfileUpdateResponse com uid, nome e departamento atualizados.

        Raises:
            HTTPException: 404 se o perfil não existir; 422 se um papel não
                orientador tentar editar departamento; 404 se o orientador não
                possuir documento advisors vinculado.
        """
        doc = await self._users.get(user.uid)
        if doc is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Perfil de usuário não encontrado",
            )

        if data.departamento is not None and user.role != "orientador":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Campo departamento editável apenas por orientador",
            )

        agora = datetime.now(timezone.utc)
        update_data: dict[str, Any] = {"nome": data.nome, "atualizado_em": agora}
        if "telefone" in doc:
            update_data["telefone"] = firestore.DELETE_FIELD
        await self._users.update(user.uid, update_data)

        departamento: str | None = None
        if user.role == "orientador" and data.departamento is not None:
            departamento = await self._atualizar_departamento(
                doc, user.uid, data.departamento, agora
            )

        return ProfileUpdateResponse(
            uid=user.uid, nome=data.nome, departamento=departamento
        )

    async def _atualizar_departamento(
        self,
        user_doc: dict[str, Any],
        uid: str,
        departamento: str,
        agora: datetime,
    ) -> str:
        """Grava o departamento no documento advisors vinculado ao orientador.

        O advisors é localizado por `users.advisor_id` quando presente; caso
        contrário, por consulta na coleção advisors filtrando por uid.
        """
        advisor_id = user_doc.get("advisor_id")
        if advisor_id is None:
            matches = await self._advisors.query(
                filters=[("uid", "==", uid)], limit=1
            )
            if matches:
                advisor_id = matches[0]["id"]
        if advisor_id is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Registro de orientador não encontrado",
            )

        await self._advisors.update(
            advisor_id, {"departamento": departamento, "atualizado_em": agora}
        )
        return departamento

    def _email_ja_tem_conta(self, email: str) -> bool:
        """Verifica no Firebase Auth se já existe conta para o e-mail."""
        try:
            self._auth.get_user_by_email(email)
        except firebase_auth.UserNotFoundError:
            return False
        return True
