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
