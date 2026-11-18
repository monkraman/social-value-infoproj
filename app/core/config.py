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
    LLM_PROVIDER: str = "auto"  # 'auto', 'azure', 'gemini', 'openai', 'offline'
    # Providers tried next, in order, when the first is out of quota or down, e.g. "gemini,openai".
    LLM_FALLBACK: str = ""
    # Which provider makes document embeddings: 'auto' (Gemini if configured, else OpenAI).
    # Independent of LLM_PROVIDER so switching chat model never invalidates the document index.
    EMBEDDING_PROVIDER: str = "auto"

    # Azure OpenAI (keys only in the backend environment: .env locally, App Service settings / Key Vault when deployed)
    AZURE_OPENAI_API_KEY: Optional[str] = None
    AZURE_OPENAI_ENDPOINT: Optional[str] = None  # e.g. https://<resource>.openai.azure.com/
    AZURE_OPENAI_DEPLOYMENT: Optional[str] = None  # the deployment name chosen in Foundry, not the model name
    AZURE_OPENAI_API_VERSION: str = "2024-10-21"
    AZURE_OPENAI_TIMEOUT_SECONDS: float = 120.0
    # Leave unset for reasoning models (gpt-5, o-series), which accept only their default temperature.
    AZURE_OPENAI_TEMPERATURE: Optional[float] = None

    # Google Gemini Settings (Free Tier available at ai.google.dev)
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-3.5-flash"
    # Tried in order when GEMINI_MODEL is over quota, overloaded, retired or times out
    GEMINI_FALLBACK_MODELS: str = "gemini-3.5-flash,gemini-flash-lite-latest,gemini-3.5-flash-lite"
    GEMINI_EMBEDDING_MODEL: str = "gemini-embedding-001"
    # Seconds to wait for one model before falling back (large JSON generations need time)
    GEMINI_GENERATION_TIMEOUT_SECONDS: float = 90.0
    # Ceiling across every model tried for a single request. Without it the fallbacks stack:
    # four models at the per-model timeout is ten minutes, by which time the caller has given up
    # and the user sees a connection error rather than a useful one.
    GEMINI_TOTAL_TIMEOUT_SECONDS: float = 200.0
    GEMINI_INTERPRET_TIMEOUT_SECONDS: float = 30.0

    # OpenAI Settings
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_CHAT_MODEL: str = "gpt-4o-mini"
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"
    EMBEDDING_DIMENSION: int = 1536
    # Placeholder vectors carry no meaning, so search over them returns noise. Only for local
    # development or tests without an AI key; never enable it on a deployed environment.
    EMBEDDING_ALLOW_SYNTHETIC: bool = False

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
        "https://frontend-social-value-tool.vercel.app,"
        "https://socialvalue.monkspaces.com,"
        "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000,http://127.0.0.1:3000"
    )
    # Extra origins matched by pattern: this project's Vercel preview deployments only.
    CORS_ORIGIN_REGEX: str = r"^https://frontend-social-value-tool(-[a-z0-9-]+)?\.vercel\.app$"
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
    def is_azure_configured(self) -> bool:
        return bool(
            (self.AZURE_OPENAI_API_KEY or "").strip()
            and (self.AZURE_OPENAI_ENDPOINT or "").strip()
            and (self.AZURE_OPENAI_DEPLOYMENT or "").strip()
            and not self.AZURE_OPENAI_API_KEY.startswith("your_")
        )

    def _chat_configured(self, provider: str) -> bool:
        return {"azure": self.is_azure_configured, "gemini": self.is_gemini_configured,
                "openai": self.is_openai_configured}.get(provider, False)

    @property
    def provider_order(self) -> list:
        """Chat providers to try, in order: the active one, then LLM_FALLBACK. Unconfigured ones are skipped."""
        first = self.active_provider
        wanted = [first] + [p.strip().lower() for p in self.LLM_FALLBACK.split(",")]
        return [p for i, p in enumerate(wanted) if p and self._chat_configured(p) and p not in wanted[:i]]

    @property
    def embedding_provider(self) -> str:
        """Embeddings stay on one provider whatever the chat provider is: vectors from different
        providers cannot be compared, so switching it means re-indexing every document."""
        prov = self.EMBEDDING_PROVIDER.lower().strip()
        if prov in ("gemini", "openai"):
            return prov if self._chat_configured(prov) else "none"
        if self.is_gemini_configured:
            return "gemini"
        return "openai" if self.is_openai_configured else "none"

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

        if prov == "azure" and self.is_azure_configured:
            return "azure"
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
        return self.active_provider in ["azure", "gemini", "openai"]

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
