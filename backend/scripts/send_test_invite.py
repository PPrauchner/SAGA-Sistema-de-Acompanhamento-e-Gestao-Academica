"""
Utilitário de DESENVOLVIMENTO/TESTE para enviar o e-mail de convite de primeiro acesso.

Isola a parte de envio (issue #81): renderiza o e-mail de convite real e o envia
pelo provedor configurado em settings (EMAIL_PROVIDER + SMTP_*), sem tocar no
Firebase Auth nem no Firestore. Serve para validar a configuração de SMTP (ex: uma
caixa Mailtrap) antes do fluxo completo de POST /api/v1/auth/invite.

Uso (a partir da raiz do repositório, com o venv e o .env configurados):
    .venv/Scripts/python.exe backend/scripts/send_test_invite.py aluno@teste.com
    .venv/Scripts/python.exe backend/scripts/send_test_invite.py aluno@teste.com --nome "Aluno Teste"

Não faz parte da feature — é só uma ajuda de teste manual.
"""

from __future__ import annotations

import argparse
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Garante que `backend.*` seja importável ao rodar o arquivo diretamente.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend.app.core.config import settings  # noqa: E402
from backend.app.core.email import EmailError, get_email_sender  # noqa: E402
from backend.app.services.auth_service import _render_invite_email  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Envia um e-mail de convite de teste.")
    parser.add_argument("email", help="E-mail do destinatário.")
    parser.add_argument("--nome", default="Convidado de Teste")
    args = parser.parse_args()

    token = str(uuid.uuid4())
    expira_em = datetime.now(timezone.utc) + timedelta(hours=48)
    link = f"{settings.frontend_url}/first-access"
    corpo = _render_invite_email(args.nome, link, token, expira_em)

    print(f"Provedor: {settings.email_provider} | SMTP_HOST={settings.smtp_host or '(vazio)'}")
    try:
        get_email_sender().send(
            args.email, "SAGA — Convite de primeiro acesso", corpo
        )
    except EmailError as exc:
        print(f"FALHA no envio: {exc}")
        raise SystemExit(1)

    print(f"E-mail enviado para {args.email} (token de teste: {token})")


if __name__ == "__main__":
    main()
