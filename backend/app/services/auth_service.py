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
from firebase_admin import exceptions as firebase_exceptions

from backend.app.core.auth import CurrentUser
from backend.app.core.config import settings
from backend.app.core.email import EmailError, EmailSender, get_email_sender
from backend.app.core.firebase import get_auth_client
from backend.app.models.user import (
    FirstAccessResponse,
    InviteRequest,
    InviteResponse,
    NotificationPreferences,
    UserResponse,
)
from backend.app.repositories.department_repository import DepartmentRepository
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
    return f"""\
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background-color:#f4f6f9;padding:24px 0;font-family:Arial,Helvetica,sans-serif;">
  <tr><td align="center">
    <table role="presentation" width="600" cellpadding="0" cellspacing="0" style="max-width:600px;background-color:#ffffff;border:1px solid #e2e8f0;border-radius:8px;overflow:hidden;">
      <tr><td style="background-color:#123C7A;padding:24px 32px;">
        <div style="color:#ffffff;font-size:22px;font-weight:bold;letter-spacing:1px;">SAGA</div>
        <div style="color:#cdd9ee;font-size:13px;margin-top:4px;">Sistema de Acompanhamento e Gestão Acadêmica</div>
      </td></tr>
      <tr><td style="padding:32px;">
        <p style="font-size:16px;color:#1a202c;margin:0 0 16px;">Olá, {nome}!</p>
        <p style="font-size:14px;color:#4a5568;line-height:1.6;margin:0 0 24px;">
          Você foi convidado para acessar o <strong>SAGA</strong>. Para definir sua senha
          e ativar sua conta, acesse a página de primeiro acesso e informe o código abaixo.
        </p>
        <div style="text-align:center;margin:0 0 24px;">
          <div style="font-size:12px;color:#718096;text-transform:uppercase;letter-spacing:1px;margin-bottom:8px;">Código de primeiro acesso</div>
          <div style="display:inline-block;background-color:#f1f5f9;border:1px dashed #94a3b8;border-radius:6px;padding:12px 20px;font-family:'Courier New',monospace;font-size:16px;color:#123C7A;letter-spacing:1px;">{token}</div>
        </div>
        <div style="text-align:center;margin:0 0 24px;">
          <a href="{link}" style="display:inline-block;background-color:#123C7A;color:#ffffff;text-decoration:none;font-size:15px;font-weight:bold;padding:12px 28px;border-radius:6px;">Acessar primeiro acesso</a>
        </div>
        <p style="font-size:13px;color:#718096;line-height:1.6;margin:0;">
          Este código é válido até <strong>{validade}</strong> (48 horas após o envio).
          Se você não esperava este convite, ignore este e-mail.
        </p>
      </td></tr>
      <tr><td style="background-color:#f8fafc;padding:16px 32px;border-top:1px solid #e2e8f0;">
        <span style="font-size:12px;color:#a0aec0;">SAGA — mensagem automática, não responda este e-mail.</span>
      </td></tr>
    </table>
  </td></tr>
</table>"""


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
        department_repo: DepartmentRepository | None = None,
    ) -> None:
        self._invites = invite_repo or FirebaseRepository("invites")
        self._users = user_repo or FirebaseRepository("users")
        self._auth = auth_client if auth_client is not None else get_auth_client()
        self._email = email_sender if email_sender is not None else get_email_sender()
        self._departments = department_repo or DepartmentRepository()

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
        if await self._email_ja_tem_conta(data.email):
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

        user_record = await asyncio.to_thread(
            self._auth.create_user, email=invite["email"], password=senha
        )
        uid = user_record.uid

        await self._provision_user_from_invite(uid, invite, token)

        return FirstAccessResponse(
            message="Conta ativada com sucesso",
            uid=uid,
            role=invite["role"],
            email=invite["email"],
        )

    async def _provision_user_from_invite(self, uid: str, invite: dict[str, Any], token: str) -> None:
        """Provisiona as claims, usuário no Firestore e atualiza referências e convite."""
        claims = {"role": invite["role"], "programa_id": invite["programa_id"]}
        await asyncio.to_thread(self._auth.set_custom_user_claims, uid, claims)

        agora = datetime.now(timezone.utc)
        user_data = {
            "uid": uid,
            "email": invite["email"],
            "nome": invite["nome"],
            "role": invite["role"],
            "programa_id": invite["programa_id"],
            "ativo": True,
            "notification_preferences": NotificationPreferences().model_dump(),
            "primeiro_acesso_completo": True,
            "criado_em": agora,
            "atualizado_em": agora,
        }
        if invite.get("student_id"):
            user_data["student_id"] = invite["student_id"]
        if invite.get("advisor_id"):
            user_data["advisor_id"] = invite["advisor_id"]

        await self._users.set(uid, user_data)

        if invite.get("student_id"):
            await FirebaseRepository("students").update(invite["student_id"], {"uid": uid})
        if invite.get("advisor_id"):
            await FirebaseRepository("advisors").update(invite["advisor_id"], {"uid": uid})

        await self._invites.update(token, {"usado": True})

    async def activate_google_first_access(
        self, id_token: str
    ) -> FirstAccessResponse:
        """Ativa a conta do convidado via Google OAuth (sem senha nem token).

        Args:
            id_token: Token JWT do Firebase retornado após signInWithPopup no Google.

        Returns:
            FirstAccessResponse com uid, role e e-mail da conta ativada.

        Raises:
            HTTPException: 401 se token inválido, 400 se sem e-mail, 403 se não houver convite.
        """
        try:
            decoded = await asyncio.to_thread(self._auth.verify_id_token, id_token)
        except (ValueError, firebase_exceptions.FirebaseError) as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token inválido ou expirado",
            ) from exc

        email = decoded.get("email")
        if not email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Token Google não possui e-mail",
            )
        
        if decoded.get("email_verified") is not True:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="E-mail não verificado pelo provedor",
            )

        firebase_sign_in_provider = decoded.get("firebase", {}).get("sign_in_provider")
        if firebase_sign_in_provider != "google.com":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Login deve ser realizado via Google",
            )
        
        email = email.lower().strip()
        
        uid = decoded["uid"]

        invites = await self._invites.query(
            filters=[("email", "==", email), ("usado", "==", False)]
        )
        agora = datetime.now(timezone.utc)
        valid_invites = [
            inv for inv in invites if inv.get("expira_em") and inv["expira_em"] > agora
        ]
        
        if not valid_invites:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="E-mail sem convite; procure a coordenação",
            )
            
        invite = valid_invites[0]
        token = invite["id"]

        await self._provision_user_from_invite(uid, invite, token)

        return FirstAccessResponse(
            message="Conta ativada com sucesso via Google",
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

        departamento = await self._departments.get_nome_by_programa(doc["programa_id"])

        return UserResponse(
            uid=doc["uid"],
            email=doc["email"],
            nome=doc["nome"],
            role=doc["role"],
            programa_id=doc["programa_id"],
            ativo=doc.get("ativo", True),
            notification_preferences=doc.get("notification_preferences", {}),
            student_id=doc.get("student_id"),
            advisor_id=doc.get("advisor_id"),
            departamento=departamento,
        )

    async def _email_ja_tem_conta(self, email: str) -> bool:
        """Verifica no Firebase Auth se já existe conta para o e-mail."""
        try:
            await asyncio.to_thread(self._auth.get_user_by_email, email)
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
