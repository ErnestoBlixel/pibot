"""
Configuración centralizada de PiBot.
Carga variables desde .env usando pydantic-settings.
"""

from pydantic_settings import BaseSettings
from pydantic import field_validator


class Settings(BaseSettings):
    """Configuración del sistema — todas las variables críticas se validan al arrancar."""

    # -- LLM (OpenRouter) --
    OPENROUTER_API_KEY: str
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
    OPENROUTER_MODEL: str = "anthropic/claude-sonnet-4-5"

    # -- Voz (OpenAI Whisper + TTS) --
    OPENAI_API_KEY: str = ""
    STT_PROVIDER: str = "openai"
    TTS_PROVIDER: str = "openai"
    TTS_VOICE: str = "alloy"

    # -- Base de datos --
    DATABASE_URL: str
    REDIS_URL: str = "redis://localhost:6379/0"

    # -- Telegram --
    TELEGRAM_BOT_TOKEN: str
    TELEGRAM_CHAT_ID_ERNESTO: str = ""
    TELEGRAM_CHAT_ID_MARTA: str = ""

    # -- n8n --
    N8N_BASE_URL: str = "http://localhost:5678"
    N8N_WEBHOOK_SECRET: str

    # -- Seguridad --
    AGENT_AUTH_TOKEN: str
    JWT_SECRET: str

    # -- Entorno --
    ENVIRONMENT: str = "production"
    LOG_LEVEL: str = "INFO"

    @field_validator("OPENROUTER_API_KEY", "DATABASE_URL", "TELEGRAM_BOT_TOKEN")
    @classmethod
    def must_not_be_empty(cls, v: str, info) -> str:
        if not v or not v.strip():
            raise ValueError(f"{info.field_name} no puede estar vacío")
        return v

    @property
    def allowed_chat_ids(self) -> set[str]:
        ids = set()
        if self.TELEGRAM_CHAT_ID_ERNESTO:
            ids.add(self.TELEGRAM_CHAT_ID_ERNESTO)
        if self.TELEGRAM_CHAT_ID_MARTA:
            ids.add(self.TELEGRAM_CHAT_ID_MARTA)
        return ids

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


settings = Settings()
