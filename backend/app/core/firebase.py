"""
Inicialização do Firebase Admin SDK e utilitários de acesso ao Firestore.
"""

from __future__ import annotations

from typing import Any

import firebase_admin
from firebase_admin import auth, credentials, firestore, storage
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
    existing_app = _get_default_app()
    if existing_app is not None:
        return existing_app

    options: dict[str, Any] = {"projectId": settings.firebase_project_id}
    if settings.firebase_storage_bucket:
        options["storageBucket"] = settings.firebase_storage_bucket

    return firebase_admin.initialize_app(_build_credentials(), options=options)


def shutdown_firebase() -> None:
    app = _get_default_app()
    if app is not None:
        firebase_admin.delete_app(app)


def is_initialized() -> bool:
    return _get_default_app() is not None


def get_firestore_client(app: App | None = None) -> Client:
    """Retorna o cliente Firestore associado à app informada.

    Seam de injeção para testes: passe uma app Firebase nomeada (ex: a app
    de integração criada pela fixture `firestore_client`) para obter um
    client apontando para o projeto de teste, sem tocar na app default de
    produção/dev. Sem argumento, mantém o comportamento original
    (usa/inicializa a app default via init_firebase()).
    """

    return firestore.client(app=app or init_firebase())


def get_auth_client() -> auth.Client:
    return auth.Client(init_firebase())


def get_storage_bucket() -> Bucket:
    if not settings.firebase_storage_bucket:
        raise RuntimeError(
            "FIREBASE_STORAGE_BUCKET não configurado: upload de arquivos indisponível",
        )

    return storage.bucket(app=init_firebase())