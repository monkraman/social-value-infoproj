import os
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "Infosys Social Value RFP Response Builder POC"
    APP_ENV: str = "development"
    APP_PORT: int = 8000
    DEBUG: bool = True

    # Multi-Provider LLM & Embedding Settings
    LLM_PROVIDER: str = "auto"  # 'auto', 'gemini', 'openai', 'offline'

    # Google Gemini Settings (Free Tier available at ai.google.dev)
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-3.5-flash"
    GEMINI_EMBEDDING_MODEL: str = "gemini-embedding-001"

    # OpenAI Settings
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_CHAT_MODEL: str = "gpt-4o-mini"
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"
    EMBEDDING_DIMENSION: int = 1536

    # Database Settings
    DATABASE_URL: str = "postgresql+psycopg://postgres@127.0.0.1:5434/social_value_db"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @property
    def active_provider(self) -> str:
        prov = self.LLM_PROVIDER.lower().strip()
        has_gemini = bool(self.GEMINI_API_KEY and self.GEMINI_API_KEY.strip() and not self.GEMINI_API_KEY.startswith("your_"))
        has_openai = bool(self.OPENAI_API_KEY and self.OPENAI_API_KEY.strip() and not self.OPENAI_API_KEY.startswith("your_"))

        if prov == "gemini" and has_gemini:
            return "gemini"
        if prov == "openai" and has_openai:
            return "openai"
        if prov == "offline":
            return "offline"

        # Auto detection
        if has_gemini:
            return "gemini"
        if has_openai:
            return "openai"
        return "offline"

    @property
    def is_ai_configured(self) -> bool:
        return self.active_provider in ["gemini", "openai"]

    @property
    def is_openai_configured(self) -> bool:
        return bool(self.OPENAI_API_KEY and self.OPENAI_API_KEY.strip() and not self.OPENAI_API_KEY.startswith("your_"))

    @property
    def is_gemini_configured(self) -> bool:
        return bool(self.GEMINI_API_KEY and self.GEMINI_API_KEY.strip() and not self.GEMINI_API_KEY.startswith("your_"))


settings = Settings()
