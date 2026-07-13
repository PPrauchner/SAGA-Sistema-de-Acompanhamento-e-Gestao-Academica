"""
Inicialização do Firebase Admin SDK e utilitários de acesso ao Firestore.

Responsabilidades:
- Inicializar o firebase_admin com as credenciais lidas de backend/app/core/config.py
  (FIREBASE_PROJECT_ID, FIREBASE_PRIVATE_KEY, FIREBASE_CLIENT_EMAIL) uma única vez no
  lifespan do FastAPI.
- Expor função `get_firestore_client() -> AsyncClient` retornando o cliente Firestore assíncrono
  reutilizado por todos os repositórios.
- Expor função `get_auth_client()` retornando o cliente firebase_admin.auth para verificação de
  tokens e gestão de custom claims.
- Expor função `get_storage_bucket()` retornando o bucket do Firebase Storage (configurado via
  FIREBASE_STORAGE_BUCKET) usado pelo upload de comprovantes.
- Garantir que o SDK seja encerrado corretamente no shutdown do lifespan.
"""

from __future__ import annotations

from typing import Any

import firebase_admin
from firebase_admin import App, auth, credentials, firestore, storage
from google.cloud.firestore import Client
from google.cloud.storage import Bucket

from backend.app.core.config import settings


def _get_default_app() -> App | None:
    try:
        return firebase_admin.get_app()
    except ValueError:
        return None


def _build_credentials() -> credentials.Certificate:
    required_settings = {
        "FIREBASE_PROJECT_ID": settings.firebase_project_id,
        "FIREBASE_PRIVATE_KEY": settings.firebase_private_key,
        "FIREBASE_CLIENT_EMAIL": settings.firebase_client_email,
    }
    missing = [name for name, value in required_settings.items() if not value]

    if missing:
        joined = ", ".join(missing)
        raise RuntimeError(f"Variáveis de ambiente Firebase ausentes: {joined}")

    private_key = settings.firebase_private_key.replace("\\n", "\n")
    return credentials.Certificate(
        {
            "type": "service_account",
            "project_id": settings.firebase_project_id,
            "private_key": private_key,
            "client_email": settings.firebase_client_email,
            "token_uri": "https://oauth2.googleapis.com/token",
        }
    )


def init_firebase() -> App:
    """Inicializa o Firebase Admin SDK uma única vez e retorna a app default."""

    existing_app = _get_default_app()
    if existing_app is not None:
        return existing_app

    options: dict[str, Any] = {"projectId": settings.firebase_project_id}
    if settings.firebase_storage_bucket:
        options["storageBucket"] = settings.firebase_storage_bucket

    return firebase_admin.initialize_app(_build_credentials(), options=options)


def shutdown_firebase() -> None:
    """Encerra a app default do Firebase Admin SDK, se ela estiver ativa."""

    app = _get_default_app()
    if app is not None:
        firebase_admin.delete_app(app)


def is_initialized() -> bool:
    return _get_default_app() is not None


def get_firestore_client(app: App | None = None) -> Client:
    """Retorna o cliente Firestore associado à app informada.

    Seam de injeção para testes: passe uma app Firebase nomeada (ex: a app de
    integração criada pela fixture `firestore_client`) para obter um client
    apontando para o projeto de teste, sem tocar na app default. Sem argumento,
    reutiliza/inicializa a app default via `init_firebase()`.

    Args:
        app: App Firebase a usar; None usa a app default.

    Returns:
        Cliente Firestore da app escolhida.
    """

    return firestore.client(app=app or init_firebase())


def get_auth_client() -> auth.Client:
    """Retorna o cliente Firebase Auth associado à app default."""

    return auth.Client(init_firebase())


def get_storage_bucket() -> Bucket:
    """Retorna o bucket do Firebase Storage (FIREBASE_STORAGE_BUCKET) da app default.

    Raises:
        RuntimeError: Se FIREBASE_STORAGE_BUCKET não estiver configurado — falha com
            mensagem explícita em vez do ValueError opaco do firebase_admin.
    """

    if not settings.firebase_storage_bucket:
        raise RuntimeError(
            "FIREBASE_STORAGE_BUCKET não configurado: upload de arquivos indisponível",
        )

    return storage.bucket(app=init_firebase())
