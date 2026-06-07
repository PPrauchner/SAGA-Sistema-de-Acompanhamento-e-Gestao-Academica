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
    """Configurações carregadas do ambiente e do arquivo .env da raiz."""

    firebase_project_id: str | None = None
    firebase_private_key: str | None = None
    firebase_client_email: str | None = None
    firebase_storage_bucket: str | None = None
    api_version: str = "v1"
    cors_origins: str = "*"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
