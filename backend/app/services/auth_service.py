"""
Serviço de negócio do fluxo de autenticação por convite.

Responsabilidades:
- create_invite: coordenação cria convite de primeiro acesso (UUID token, TTL 48h),
  persistindo em invites/{token}; rejeita e-mail que já possui conta ativa (409). Após
  persistir, envia ao convidado um e-mail com o link de primeiro acesso, o código e a
  validade; falha de envio é registrada em log e não derruba o convite.
- activate_first_access: valida o convite (existe + não expirado + não usado), cria o
  usuário no Firebase Auth com a senha informada, define os custom claims
  {role, programa_id}, cria o documento users/{uid} e marca o convite como usado.
- get_me: retorna o perfil do usuário autenticado a partir de users/{uid}.

O backend nunca recebe a senha em nenhum outro ponto — apenas aqui, repassada
diretamente ao Firebase Admin SDK na criação da conta.

Referência: docs/specs/04_autenticacao.json (fluxo_primeiro_acesso, contratos_api).
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import HTTPException, status
from firebase_admin import auth as firebase_auth

from backend.app.core.auth import CurrentUser
from backend.app.core.config import settings
from backend.app.core.email import EmailError, EmailSender, get_email_sender
from backend.app.core.firebase import get_auth_client
from backend.app.models.user import (
    FirstAccessResponse,
    InviteRequest,
    InviteResponse,
    UserResponse,
)
from backend.app.repositories.firebase_repository import FirebaseRepository

logger = logging.getLogger(__name__)

# Tempo de validade do convite de primeiro acesso.
_INVITE_TTL = timedelta(hours=48)


def _render_invite_email(
    nome: str, link: str, token: str, expira_em: datetime
) -> str:
    """Monta o corpo HTML do e-mail de convite de primeiro acesso.

    Args:
        nome: Nome do convidado, usado na saudação.
        link: URL da página de primeiro acesso no frontend.
        token: UUID do convite (código a informar na tela de primeiro acesso).
        expira_em: Instante de expiração do convite.

    Returns:
        Corpo do e-mail em HTML.
    """
    validade = expira_em.strftime("%d/%m/%Y %H:%M UTC")
    return (
        f"<p>Olá, {nome}!</p>"
        f"<p>Você foi convidado para acessar o SAGA. Acesse "
        f'<a href="{link}">{link}</a> e informe o código abaixo na tela de '
        f"primeiro acesso para definir sua senha:</p>"
        f'<p style="font-size:18px;font-weight:bold">{token}</p>'
        f"<p>Este código é válido até {validade} (48 horas após o envio).</p>"
    )


class AuthService:
    """Orquestra convite, ativação de conta e leitura de perfil.

    As dependências (repositórios e cliente de auth) são injetáveis para
    facilitar testes; em produção usam as implementações reais por padrão.
    """

    def __init__(
        self,
        invite_repo: FirebaseRepository | None = None,
        user_repo: FirebaseRepository | None = None,
        auth_client: Any | None = None,
        email_sender: EmailSender | None = None,
    ) -> None:
        self._invites = invite_repo or FirebaseRepository("invites")
        self._users = user_repo or FirebaseRepository("users")
        self._auth = auth_client if auth_client is not None else get_auth_client()
        self._email = email_sender if email_sender is not None else get_email_sender()

    async def create_invite(
        self,
        data: InviteRequest,
        current_user: CurrentUser,
        extra_fields: dict[str, Any] | None = None,
    ) -> InviteResponse:
        """Cria um convite de primeiro acesso para o e-mail informado.

        Args:
            data: E-mail, papel e nome do convidado.
            current_user: Coordenação autenticada que emite o convite.

        Returns:
            InviteResponse com o token e a data de expiração (ISO8601).

        Raises:
            HTTPException: 409 se o e-mail já possui conta ativa no Firebase Auth.
        """
        if self._email_ja_tem_conta(data.email):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="E-mail já possui conta ativa",
            )

        token = str(uuid.uuid4())
        agora = datetime.now(timezone.utc)
        expira_em = agora + _INVITE_TTL

        invite_data = {
                "email": data.email,
                "role": data.role,
                "nome": data.nome,
                "programa_id": current_user.programa_id,
                "usado": False,
                "expira_em": expira_em,
                "criado_por": current_user.uid,
                "criado_em": agora,
        }
        if extra_fields:
            invite_data.update(extra_fields)

        await self._invites.set(token, invite_data)

        await self._enviar_email_convite(data.email, data.nome, token, expira_em)

        return InviteResponse(
            message=f"Convite enviado para {data.email}",
            token=token if settings.expose_invite_token else None,
            expira_em=expira_em.isoformat(),
        )

    async def _enviar_email_convite(
        self, email: str, nome: str, token: str, expira_em: datetime
    ) -> None:
        """Envia o e-mail de convite com o link de primeiro acesso.

        O convite já está persistido quando este método roda; uma falha de envio
        é registrada em log e não propaga, para não deixar o convite em estado
        inconsistente (o token segue válido e disponível como fallback de dev).

        Args:
            email: Destinatário do convite.
            nome: Nome do convidado, usado na saudação.
            token: UUID do convite (código de primeiro acesso).
            expira_em: Instante de expiração do convite.
        """
        link = f"{settings.frontend_url}/first-access"
        assunto = "SAGA — Convite de primeiro acesso"
        corpo = _render_invite_email(nome, link, token, expira_em)
        try:
            await asyncio.to_thread(self._email.send, email, assunto, corpo)
        except EmailError as exc:
            logger.error(
                "Falha ao enviar e-mail de convite para %s: %s", email, exc
            )

    async def activate_first_access(
        self, token: str, senha: str
    ) -> FirstAccessResponse:
        """Ativa a conta do convidado: cria usuário, claims e perfil.

        Args:
            token: UUID do convite recebido por e-mail.
            senha: Senha escolhida pelo usuário (já validada pelo modelo).

        Returns:
            FirstAccessResponse com uid, role e e-mail da conta ativada.

        Raises:
            HTTPException: 400 se o token for inválido, expirado ou já utilizado.
        """
        invite = self._validar_convite(await self._invites.get(token))

        user_record = self._auth.create_user(email=invite["email"], password=senha)
        uid = user_record.uid

        claims = {"role": invite["role"], "programa_id": invite["programa_id"]}
        self._auth.set_custom_user_claims(uid, claims)

        agora = datetime.now(timezone.utc)
        user_data = {
            "uid": uid,
            "email": invite["email"],
            "nome": invite["nome"],
            "role": invite["role"],
            "programa_id": invite["programa_id"],
            "ativo": True,
            "primeiro_acesso_completo": True,
            "criado_em": agora,
            "atualizado_em": agora,
        }
        if invite.get("student_id"):
            user_data["student_id"] = invite["student_id"]
        if invite.get("advisor_id"):
            user_data["advisor_id"] = invite["advisor_id"]

        await self._users.set(
            uid,
            user_data,
        )

        if invite.get("student_id"):
            await FirebaseRepository("students").update(invite["student_id"], {"uid": uid})
        if invite.get("advisor_id"):
            await FirebaseRepository("advisors").update(invite["advisor_id"], {"uid": uid})

        await self._invites.update(token, {"usado": True})

        return FirstAccessResponse(
            message="Conta ativada com sucesso",
            uid=uid,
            role=invite["role"],
            email=invite["email"],
        )

    async def get_me(self, current_user: CurrentUser) -> UserResponse:
        """Retorna o perfil do usuário autenticado a partir de users/{uid}.

        Args:
            current_user: Identidade extraída do JWT pela dependência de auth.

        Returns:
            UserResponse com os dados de perfil.

        Raises:
            HTTPException: 404 se o documento de perfil não existir.
        """
        doc = await self._users.get(current_user.uid)
        if doc is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Perfil de usuário não encontrado",
            )

        return UserResponse(
            uid=doc["uid"],
            email=doc["email"],
            nome=doc["nome"],
            role=doc["role"],
            programa_id=doc["programa_id"],
            ativo=doc.get("ativo", True),
            student_id=doc.get("student_id"),
            advisor_id=doc.get("advisor_id"),
        )

    def _email_ja_tem_conta(self, email: str) -> bool:
        """Verifica no Firebase Auth se já existe conta para o e-mail."""
        try:
            self._auth.get_user_by_email(email)
        except firebase_auth.UserNotFoundError:
            return False
        return True

    @staticmethod
    def _validar_convite(invite: dict[str, Any] | None) -> dict[str, Any]:
        """Garante que o convite existe, não foi usado e não expirou.

        Args:
            invite: Documento do convite lido do Firestore, ou None se ausente.

        Returns:
            O convite validado (garantidamente não-None).

        Raises:
            HTTPException: 400 se o token for inválido, expirado ou já utilizado.
        """
        if invite is None or invite.get("usado"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Token inválido, expirado ou já utilizado",
            )
        if datetime.now(timezone.utc) > invite["expira_em"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Token inválido, expirado ou já utilizado",
            )
        return invite
