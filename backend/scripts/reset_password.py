"""
Redefine a senha de uma conta diretamente no Firebase Auth via Admin SDK.

Responsabilidades:
- Inicializar o Firebase Admin SDK com as credenciais do ambiente.
- Localizar a conta por e-mail (--email) ou por UID (--uid).
- Sobrescrever a senha com auth.update_user(uid, password=...).

A troca é silenciosa: o Admin SDK NÃO dispara e-mail de recuperação nem de
notificação. Por isso funciona com contas de teste de e-mail fictício.

Uso (rodar da raiz do repo, com a .venv ativa):
    python backend/scripts/reset_password.py --email teste@saga.local --senha NovaSenha123
    python backend/scripts/reset_password.py --uid abc123XYZ --senha NovaSenha123
"""

from __future__ import annotations

import argparse
import sys

from firebase_admin import auth

from backend.app.core.firebase import init_firebase, shutdown_firebase

# Comprimento mínimo de senha exigido pelo Firebase Auth.
MIN_SENHA_LEN = 6


def redefinir_senha(senha: str, email: str | None, uid: str | None) -> str:
    """Redefine a senha da conta identificada por e-mail ou UID.

    Args:
        senha: Nova senha (mínimo 6 caracteres).
        email: E-mail da conta, ou None se identificada por UID.
        uid: UID da conta, ou None se identificada por e-mail.

    Returns:
        O UID da conta cuja senha foi redefinida.

    Raises:
        ValueError: Se a senha for menor que MIN_SENHA_LEN.
        firebase_admin.auth.UserNotFoundError: Se a conta não existir.
    """
    if len(senha) < MIN_SENHA_LEN:
        raise ValueError(f"A senha deve ter ao menos {MIN_SENHA_LEN} caracteres.")

    user = auth.get_user(uid) if uid else auth.get_user_by_email(email)
    auth.update_user(user.uid, password=senha)
    return user.uid


def main() -> int:
    """Faz o parse dos argumentos, redefine a senha e reporta o resultado."""
    parser = argparse.ArgumentParser(
        description="Redefine a senha de uma conta no Firebase Auth (sem enviar e-mail)."
    )
    identificador = parser.add_mutually_exclusive_group(required=True)
    identificador.add_argument("--email", help="E-mail da conta (mesmo que fictício).")
    identificador.add_argument("--uid", help="UID da conta no Firebase Auth.")
    parser.add_argument("--senha", required=True, help="Nova senha (mínimo 6 caracteres).")
    args = parser.parse_args()

    init_firebase()
    try:
        uid = redefinir_senha(args.senha, args.email, args.uid)
    except (ValueError, auth.UserNotFoundError) as erro:
        print(f"Erro: {erro}", file=sys.stderr)
        return 1
    finally:
        shutdown_firebase()

    print(f"Senha redefinida com sucesso (uid={uid}).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
