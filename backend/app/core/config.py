"""
Configurações globais da aplicação lidas de variáveis de ambiente.

Responsabilidades:
- Definir a classe Settings (via pydantic-settings) que carrega as seguintes variáveis de
  ambiente: FIREBASE_PROJECT_ID, FIREBASE_PRIVATE_KEY, FIREBASE_CLIENT_EMAIL,
  FIREBASE_STORAGE_BUCKET, API_VERSION, CORS_ORIGINS.
- Expor instância singleton `settings` importável pelos demais módulos.
- Garantir que a aplicação falhe em tempo de startup se variáveis obrigatórias estiverem ausentes.
- Centralizar constantes de configuração reutilizadas pelos aspectos (ex: dias de alerta de prazo,
  limites de prorrogação) que são importadas por backend/app/aspects/aspect_config.py.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Firebase Admin SDK
    firebase_project_id: str
    firebase_private_key: str
    firebase_client_email: str
    firebase_storage_bucket: str = ""

    # API
    api_version: str = "1.0.0-MVP"
    cors_origins: list[str] = ["http://localhost:5173"]

    # Aspect constants — importados por aspect_config.py
    deadline_alert_days: int = 30
    max_extensions: int = 2


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
