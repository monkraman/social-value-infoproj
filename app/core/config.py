import os
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
ENV_FILE_PATH = BASE_DIR / ".env"


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
    # Tried in order when GEMINI_MODEL is over quota, overloaded, retired or times out
    GEMINI_FALLBACK_MODELS: str = "gemini-3.5-flash,gemini-flash-lite-latest,gemini-3.5-flash-lite"
    GEMINI_EMBEDDING_MODEL: str = "gemini-embedding-001"
    # Seconds to wait for Gemini before falling back (large JSON generations need time)
    GEMINI_GENERATION_TIMEOUT_SECONDS: float = 150.0
    GEMINI_INTERPRET_TIMEOUT_SECONDS: float = 30.0

    # OpenAI Settings
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_CHAT_MODEL: str = "gpt-4o-mini"
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"
    EMBEDDING_DIMENSION: int = 1536

    # Security Settings
    # JWT signing key. Set a long random value in every deployed environment; if unset,
    # a random key is generated per process (sessions end on restart, but tokens can't be forged).
    JWT_SECRET_KEY: Optional[str] = None
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480  # 8-hour sessions
    # One-time bootstrap: creates this superadmin only when the users table is empty.
    INITIAL_ADMIN_EMAIL: Optional[str] = None
    INITIAL_ADMIN_PASSWORD: Optional[str] = None
    # Comma-separated browser origins allowed to call the API.
    CORS_ORIGINS: str = (
        "https://nice-moss-0c037f310.3.azurestaticapps.net,"
        "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000,http://127.0.0.1:3000"
    )
    LOGIN_MAX_FAILURES: int = 5
    LOGIN_LOCKOUT_MINUTES: int = 15

    # Database Settings (Set via .env or Azure App Service Environment Variables)
    DATABASE_URL: str = "postgresql+psycopg://postgres:postgres@localhost:5432/social_value_db"

    model_config = SettingsConfigDict(
        env_file=[str(ENV_FILE_PATH), ".env"],
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @property
    def active_provider(self) -> str:
        prov = self.LLM_PROVIDER.lower().strip()
        has_gemini = bool(
            self.GEMINI_API_KEY
            and self.GEMINI_API_KEY.strip()
            and not self.GEMINI_API_KEY.startswith("your_")
        )
        has_openai = bool(
            self.OPENAI_API_KEY
            and self.OPENAI_API_KEY.strip()
            and not self.OPENAI_API_KEY.startswith("your_")
        )

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
        return bool(
            self.OPENAI_API_KEY
            and self.OPENAI_API_KEY.strip()
            and not self.OPENAI_API_KEY.startswith("your_")
        )

    @property
    def is_gemini_configured(self) -> bool:
        return bool(
            self.GEMINI_API_KEY
            and self.GEMINI_API_KEY.strip()
            and not self.GEMINI_API_KEY.startswith("your_")
        )


settings = Settings()
