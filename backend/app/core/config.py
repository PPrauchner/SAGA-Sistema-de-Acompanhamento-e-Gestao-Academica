"""
Configurações globais da aplicação lidas de variáveis de ambiente.

Responsabilidades:
- Definir a classe Settings (via pydantic-settings) que carrega as seguintes variáveis de
  ambiente: FIREBASE_PROJECT_ID, FIREBASE_PRIVATE_KEY, FIREBASE_CLIENT_EMAIL,
  FIREBASE_STORAGE_BUCKET, API_VERSION, CORS_ORIGINS.
- Carregar as configurações de envio de e-mail (EMAIL_PROVIDER, SMTP_*, FRONTEND_URL,
  EXPOSE_INVITE_TOKEN) usadas pelo convite de primeiro acesso.
- Expor instância singleton `settings` importável pelos demais módulos.
- Garantir que a aplicação falhe em tempo de startup se variáveis obrigatórias estiverem ausentes.
- Centralizar constantes de configuração reutilizadas pelos aspectos (ex: dias de alerta de prazo,
  limites de prorrogação) que são importadas por backend/app/aspects/aspect_config.py.
"""

from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        # O .env do projeto reúne variáveis do backend e do frontend (VITE_*)
        # no mesmo arquivo (ver .env.example); ignorar chaves não mapeadas
        # evita que essas variáveis do frontend quebrem o startup do backend.
        extra="ignore",
    )

    # Firebase Admin SDK
    firebase_project_id: str
    firebase_private_key: str
    firebase_client_email: str
    firebase_storage_bucket: str = ""

    # API
    api_version: str = "1.0.0-MVP"
    cors_origins: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
    ]

    @field_validator("cors_origins", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: str | list[str]) -> list[str]:
        """Garante que strings separadas por vírgula no .env virem uma lista."""
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        return v

    # Base do frontend — usada para montar o link de primeiro acesso no e-mail de convite.
    frontend_url: str = "http://localhost:5173"

    # Envio de e-mail
    # email_provider seleciona a implementação de EmailSender em core/email.py.
    # "smtp" é a única suportada hoje; "sendgrid" pode ser adicionada sem tocar nos
    # serviços (basta uma nova classe e um ramo na factory get_email_sender()).
    email_provider: str = "smtp"
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = ""
    smtp_use_tls: bool = True

    # Token do convite na resposta da API: fallback de dev/testes. Em produção,
    # definir EXPOSE_INVITE_TOKEN=false para que o token saia apenas por e-mail.
    expose_invite_token: bool = True

    # Aspect constants — importados por aspect_config.py
    deadline_alert_days: int = 30
    max_extensions: int = 2


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
