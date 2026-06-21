"""
Testes do EmailSender (SMTP) e da factory get_email_sender.

Não tocam a rede: o transporte smtplib.SMTP é substituído por um fake via
monkeypatch nos cenários de envio.
"""

from __future__ import annotations

import smtplib

import pytest

from backend.app.core.config import settings
from backend.app.core.email import EmailError, SmtpEmailSender, get_email_sender


def test_get_email_sender_smtp() -> None:
    assert isinstance(get_email_sender(), SmtpEmailSender)


def test_get_email_sender_provedor_invalido(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "email_provider", "carteiro_pombo")
    with pytest.raises(EmailError):
        get_email_sender()


def test_smtp_send_sem_host_levanta_erro() -> None:
    sender = SmtpEmailSender(
        host="", port=587, user="", password="", sender="x@x.com", use_tls=True
    )
    with pytest.raises(EmailError):
        sender.send("dest@x.com", "assunto", "<p>oi</p>")


def test_smtp_send_monta_e_envia(monkeypatch: pytest.MonkeyPatch) -> None:
    enviados = []

    class _FakeSMTP:
        def __init__(self, host: str, port: int, timeout: int = 10) -> None:
            self.logado = False

        def __enter__(self) -> "_FakeSMTP":
            return self

        def __exit__(self, *exc: object) -> bool:
            return False

        def starttls(self) -> None:
            pass

        def login(self, user: str, password: str) -> None:
            self.logado = True

        def send_message(self, message: object) -> None:
            enviados.append(message)

    monkeypatch.setattr(smtplib, "SMTP", _FakeSMTP)
    sender = SmtpEmailSender(
        host="smtp.x.com", port=587, user="u", password="p",
        sender="from@x.com", use_tls=True,
    )

    sender.send("dest@x.com", "Assunto", "<p>corpo</p>")

    assert len(enviados) == 1
    msg = enviados[0]
    assert msg["To"] == "dest@x.com"
    assert msg["From"] == "from@x.com"
    assert msg["Subject"] == "Assunto"


def test_smtp_from_vazio_usa_user(monkeypatch: pytest.MonkeyPatch) -> None:
    enviados = []

    class _FakeSMTP:
        def __init__(self, host: str, port: int, timeout: int = 10) -> None:
            pass

        def __enter__(self) -> "_FakeSMTP":
            return self

        def __exit__(self, *exc: object) -> bool:
            return False

        def starttls(self) -> None:
            pass

        def login(self, user: str, password: str) -> None:
            pass

        def send_message(self, message: object) -> None:
            enviados.append(message)

    monkeypatch.setattr(smtplib, "SMTP", _FakeSMTP)
    sender = SmtpEmailSender(
        host="smtp.x.com", port=587, user="conta@x.com", password="p",
        sender="", use_tls=True,
    )

    sender.send("dest@x.com", "Assunto", "<p>corpo</p>")

    assert enviados[0]["From"] == "conta@x.com"


def test_smtp_send_falha_de_conexao_vira_email_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _BoomSMTP:
        def __init__(self, *args: object, **kwargs: object) -> None:
            raise OSError("connection refused")

    monkeypatch.setattr(smtplib, "SMTP", _BoomSMTP)
    sender = SmtpEmailSender(
        host="smtp.x.com", port=587, user="u", password="p",
        sender="f@x.com", use_tls=True,
    )
    with pytest.raises(EmailError):
        sender.send("d@x.com", "s", "<p>b</p>")
