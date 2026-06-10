"""
Configuração de teste para a camada de repositórios.

Injeta credenciais Firebase dummy nas variáveis de ambiente antes que
backend.app.core.config seja importado, permitindo instanciar Settings sem um
.env real. As operações de Firestore são mockadas nos testes — nenhuma
credencial verdadeira é necessária.
"""

import os

os.environ.setdefault("FIREBASE_PROJECT_ID", "test-project")
os.environ.setdefault("FIREBASE_PRIVATE_KEY", "test-key")
os.environ.setdefault("FIREBASE_CLIENT_EMAIL", "test@test-project.iam.gserviceaccount.com")
