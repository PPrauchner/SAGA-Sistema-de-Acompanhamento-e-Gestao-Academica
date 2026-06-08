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
- Garantir que o SDK seja encerrado corretamente no shutdown do lifespan.
"""

import firebase_admin
from firebase_admin import auth, credentials, firestore

from backend.app.core.config import settings

_firebase_app: firebase_admin.App | None = None


def init_firebase() -> None:
    """Inicializa o Firebase Admin SDK a partir das credenciais em settings."""
    global _firebase_app
    cred = credentials.Certificate(
        {
            "type": "service_account",
            "project_id": settings.firebase_project_id,
            # Substitui \\n literal (vindo de .env) pelo newline real
            "private_key": settings.firebase_private_key.replace("\\n", "\n"),
            "client_email": settings.firebase_client_email,
            "token_uri": "https://oauth2.googleapis.com/token",
        }
    )
    _firebase_app = firebase_admin.initialize_app(cred)


def shutdown_firebase() -> None:
    """Encerra o Firebase Admin SDK no shutdown do lifespan."""
    global _firebase_app
    if _firebase_app:
        firebase_admin.delete_app(_firebase_app)
        _firebase_app = None


def is_initialized() -> bool:
    return _firebase_app is not None


def get_firestore_client():
    """Retorna o cliente Firestore. Deve ser chamado após init_firebase()."""
    return firestore.client()


def get_auth_client():
    """Retorna o módulo firebase_admin.auth para verificação de tokens."""
    return auth
