"""
Configuração de teste para a camada de serviços.

Injeta credenciais Firebase dummy nas variáveis de ambiente antes de
backend.app.core.config ser importado, permitindo instanciar Settings sem um
.env real. Repositórios e o cliente de auth são mockados nos testes.
"""

import os

os.environ.setdefault("FIREBASE_PROJECT_ID", "test-project")
os.environ.setdefault("FIREBASE_PRIVATE_KEY", "test-key")
os.environ.setdefault("FIREBASE_CLIENT_EMAIL", "test@test-project.iam.gserviceaccount.com")
