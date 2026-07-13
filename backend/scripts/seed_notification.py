"""
Utilitário de DESENVOLVIMENTO/TESTE para semear uma notificação no Firestore.

Existe porque o aspecto A05 (@trigger_alerts) ainda não está fiado a nenhum endpoint
disparador (isso é escopo das issues #44/#48/#49/#51). Para validar a NotificationsPage
(onSnapshot + marcar como lida) na prática, este script grava um documento em
notifications/ para o usuário informado.

Uso (a partir da raiz do repositório, com o venv ativo):
    .venv/Scripts/python.exe backend/scripts/seed_notification.py coordenacao@exemplo.com
    .venv/Scripts/python.exe backend/scripts/seed_notification.py coordenacao@exemplo.com \
        --tipo prazo_critico --titulo "Prazo crítico" --mensagem "Faltam 30 dias"

Não faz parte da feature — é só uma ajuda de teste manual.
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

# Garante que `backend.*` seja importável ao rodar o arquivo diretamente.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from firebase_admin import auth  # noqa: E402

from backend.app.core.firebase import get_firestore_client, init_firebase  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Semeia uma notificação de teste.")
    parser.add_argument("email", help="E-mail do destinatário (resolvido para uid via Admin SDK).")
    parser.add_argument("--tipo", default="atividade_validada")
    parser.add_argument("--titulo", default="Notificação de teste")
    parser.add_argument("--mensagem", default="Esta é uma notificação semeada para teste manual.")
    parser.add_argument("--programa-id", default="prog_default")
    args = parser.parse_args()

    init_firebase()

    uid = auth.get_user_by_email(args.email).uid

    doc = {
        "tipo": args.tipo,
        "titulo": args.titulo,
        "mensagem": args.mensagem,
        "destinatario_id": uid,
        "entidade_tipo": None,
        "entidade_id": None,
        "lida": False,
        "timestamp": datetime.now(timezone.utc),
        "programa_id": args.programa_id,
    }

    ref = get_firestore_client().collection("notifications").document()
    ref.set(doc)

    print(f"Notificação criada: notifications/{ref.id} (destinatario_id={uid})")


if __name__ == "__main__":
    main()
