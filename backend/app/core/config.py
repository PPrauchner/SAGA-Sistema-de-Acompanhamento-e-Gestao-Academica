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
