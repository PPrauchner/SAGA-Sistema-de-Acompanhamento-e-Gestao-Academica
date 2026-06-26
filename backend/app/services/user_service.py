"""
Serviço de gestão de usuários privilegiados.

Responsabilidades:
- create_coordinator: adm cria um coordenador diretamente (sem fluxo de
  convite), definindo e-mail, senha, nome e programa no Firebase Auth e
  Firestore. Rejeita e-mail que já possui conta ativa (409).

Referência: docs/specs/04_autenticacao.json; issue #162 (US-PA05).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException, status
from firebase_admin import auth as firebase_auth

from backend.app.core.firebase import get_auth_client
from backend.app.models.user import CreateCoordinatorRequest, CreateCoordinatorResponse
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
    ) -> None:
        self._users = user_repo or FirebaseRepository("users")
        self._auth = auth_client if auth_client is not None else get_auth_client()

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

    def _email_ja_tem_conta(self, email: str) -> bool:
        """Verifica no Firebase Auth se já existe conta para o e-mail."""
        try:
            self._auth.get_user_by_email(email)
        except firebase_auth.UserNotFoundError:
            return False
        return True
