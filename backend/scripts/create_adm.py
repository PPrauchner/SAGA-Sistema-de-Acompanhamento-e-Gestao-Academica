"""
Cria uma conta de superusuário global (`adm`) diretamente no Firebase Auth e Firestore.

Responsabilidades:
- Inicializar o Firebase Admin SDK com as credenciais do ambiente.
- Criar a conta no Firebase Auth com e-mail e senha informados.
- Gravar os custom claims `{role: "adm", programa_id: None}` — o `adm` é global
  (ADR-0001) e não pertence a programa algum, por isso seu programa_id é nulo.
- Criar o documento users/{uid} espelhando os claims (role, programa_id nulo).

O papel `adm` é criado exclusivamente por este script, fora da interface; pode
haver mais de um `adm` (basta repetir o script com e-mails distintos).

Uso (rodar da raiz do repo, com a .venv ativa):
    python backend/scripts/create_adm.py --email adm@saga.local --senha SenhaForte123 --nome "Admin"
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from datetime import datetime, timezone
from pathlib import Path

# Garante que `backend.*` seja importável ao rodar o arquivo diretamente.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from firebase_admin import auth  # noqa: E402

from backend.app.core.firebase import shutdown_firebase  # noqa: E402
from backend.app.repositories.firebase_repository import FirebaseRepository  # noqa: E402

# Comprimento mínimo de senha exigido pelo Firebase Auth.
MIN_SENHA_LEN = 6


async def criar_adm(email: str, senha: str, nome: str) -> str:
    """Cria a conta `adm` no Firebase Auth e o documento users/{uid}.

    Args:
        email: E-mail da nova conta de superusuário.
        senha: Senha inicial (mínimo MIN_SENHA_LEN caracteres).
        nome: Nome exibido do superusuário.

    Returns:
        O UID da conta `adm` criada.

    Raises:
        ValueError: Se a senha for menor que MIN_SENHA_LEN.
        firebase_admin.auth.EmailAlreadyExistsError: Se o e-mail já tiver conta.
    """
    if len(senha) < MIN_SENHA_LEN:
        raise ValueError(f"A senha deve ter ao menos {MIN_SENHA_LEN} caracteres.")

    user_record = auth.create_user(email=email, password=senha)
    uid = user_record.uid

    # programa_id nulo: o `adm` é global e não pertence a nenhum programa.
    auth.set_custom_user_claims(uid, {"role": "adm", "programa_id": None})

    agora = datetime.now(timezone.utc)
    await FirebaseRepository("users").set(
        uid,
        {
            "uid": uid,
            "email": email.strip().lower(),
            "nome": nome,
            "role": "adm",
            "programa_id": None,
            "ativo": True,
            "primeiro_acesso_completo": True,
            "criado_em": agora,
            "atualizado_em": agora,
        },
    )
    return uid


def main() -> int:
    """Faz o parse dos argumentos, cria o `adm` e reporta o resultado."""
    parser = argparse.ArgumentParser(
        description="Cria um superusuário global (adm) no Firebase Auth e Firestore.",
    )
    parser.add_argument("--email", required=True, help="E-mail da conta adm.")
    parser.add_argument("--senha", required=True, help="Senha inicial (mínimo 6 caracteres).")
    parser.add_argument("--nome", required=True, help="Nome exibido do superusuário.")
    args = parser.parse_args()

    try:
        uid = asyncio.run(criar_adm(args.email, args.senha, args.nome))
    except (ValueError, auth.EmailAlreadyExistsError) as erro:
        print(f"Erro: {erro}", file=sys.stderr)
        return 1
    finally:
        shutdown_firebase()

    print(f"Superusuário adm criado com sucesso (uid={uid}).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
