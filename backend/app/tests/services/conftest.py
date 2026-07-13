"""
Configuração compartilhada dos testes de serviços (backend/app/tests/services/).

Define variáveis de ambiente Firebase dummy em nível de módulo — antes de qualquer
import de test module — porque core/config instancia Settings (pydantic-settings) no
import e exige FIREBASE_PROJECT_ID/PRIVATE_KEY/CLIENT_EMAIL. Usa setdefault para não
sobrescrever um ambiente real e evita que cada arquivo de teste mute os.environ por conta
própria (e dependa da ordem alfabética de coleta).
"""

import os

os.environ.setdefault("FIREBASE_PROJECT_ID", "test-project")
os.environ.setdefault("FIREBASE_PRIVATE_KEY", "test-key")
os.environ.setdefault("FIREBASE_CLIENT_EMAIL", "test-email")
