"""
Envio de e-mail transacional para o backend.

Responsabilidades:
- Definir a interface EmailSender (Protocol) que desacopla os serviços do provedor
  concreto: quem precisa enviar e-mail conhece apenas o método send().
- Implementar SmtpEmailSender usando exclusivamente a stdlib (smtplib + email.message),
  sem dependências externas; lê host, porta, credenciais e remetente de settings.
- Expor a factory get_email_sender() que seleciona a implementação a partir de
  settings.email_provider, permitindo adicionar provedores (ex: SendGrid) sem alterar
  os serviços — basta uma nova classe e um ramo nesta factory.

Restrições:
- A escolha do provedor acontece apenas em get_email_sender(); os serviços dependem da
  interface EmailSender, nunca de smtplib diretamente.
"""

from __future__ import annotations

import smtplib
from email.message import EmailMessage
from typing import Protocol

from backend.app.core.config import settings


class EmailError(Exception):
    """Falha ao enviar um e-mail (conexão, autenticação ou entrega)."""


class EmailSender(Protocol):
    """Contrato mínimo de envio de e-mail consumido pelos serviços."""

    def send(self, to: str, subject: str, html_body: str) -> None:
        """Envia um e-mail HTML para um destinatário.

        Args:
            to: E-mail do destinatário.
            subject: Assunto da mensagem.
            html_body: Corpo da mensagem em HTML.

        Raises:
            EmailError: Se o envio falhar.
        """
        ...


class SmtpEmailSender:
    """EmailSender baseado em SMTP, usando apenas a stdlib.

    Attributes:
        host: Servidor SMTP.
        port: Porta SMTP.
        user: Usuário de autenticação (também remetente default se sender vazio).
        password: Senha de autenticação.
        sender: Remetente exibido no campo From.
        use_tls: Se True, inicia STARTTLS antes de autenticar.
    """

    def __init__(
        self,
        host: str,
        port: int,
        user: str,
        password: str,
        sender: str,
        use_tls: bool,
    ) -> None:
        """Configura o transporte SMTP. Ver os atributos da classe."""
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.sender = sender or user
        self.use_tls = use_tls

    def send(self, to: str, subject: str, html_body: str) -> None:
        """Envia o e-mail via SMTP. Ver EmailSender.send.

        Raises:
            EmailError: Se o SMTP não estiver configurado ou o envio falhar.
        """
        if not self.host:
            raise EmailError("SMTP não configurado: defina SMTP_HOST")

        message = EmailMessage()
        message["From"] = self.sender
        message["To"] = to
        message["Subject"] = subject
        message.set_content("Seu cliente de e-mail não suporta HTML.")
        message.add_alternative(html_body, subtype="html")

        try:
            with smtplib.SMTP(self.host, self.port, timeout=10) as smtp:
                if self.use_tls:
                    smtp.starttls()
                if self.user:
                    smtp.login(self.user, self.password)
                smtp.send_message(message)
        except (smtplib.SMTPException, OSError) as exc:
            raise EmailError(f"Falha ao enviar e-mail para {to}: {exc}") from exc


def get_email_sender() -> EmailSender:
    """Devolve a implementação de EmailSender conforme settings.email_provider.

    Returns:
        Uma instância que satisfaz o protocolo EmailSender.

    Raises:
        EmailError: Se o provedor configurado não for suportado.
    """
    provider = settings.email_provider.lower()
    if provider == "smtp":
        return SmtpEmailSender(
            host=settings.smtp_host,
            port=settings.smtp_port,
            user=settings.smtp_user,
            password=settings.smtp_password,
            sender=settings.smtp_from,
            use_tls=settings.smtp_use_tls,
        )
    raise EmailError(
        f"Provedor de e-mail não suportado: {settings.email_provider}"
    )
