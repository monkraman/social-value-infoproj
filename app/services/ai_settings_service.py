"""Which AI provider answers first, as chosen by a super-administrator in the tool.

Only the choice is stored (table app_settings); keys stay in the backend environment. The stored
choice is re-read at most every few seconds, and any problem reading it falls back to the
.env order, so a database hiccup can never stop the generator.
"""
import time
from typing import List, Optional

from app.core.config import settings
from app.core.database import SessionLocal
from app.models.app_setting import AppSetting

KEY = "ai_primary_provider"
PROVIDERS = ("azure", "gemini", "openai")
_CACHE_SECONDS = 15.0
_cache = {"value": None, "at": 0.0}


def provider_model(provider: str) -> str:
    return {
        "azure": settings.AZURE_OPENAI_DEPLOYMENT or "",
        "gemini": settings.GEMINI_MODEL,
        "openai": settings.OPENAI_CHAT_MODEL,
    }.get(provider, "")


def provider_label(provider: str) -> str:
    name = {"azure": "Azure OpenAI", "gemini": "Google Gemini", "openai": "OpenAI"}.get(provider, provider)
    model = provider_model(provider)
    return f"{name} ({model})" if model else name


def stored_primary(db=None) -> Optional[str]:
    """The administrator's choice, or None to follow the .env order."""
    now = time.monotonic()
    if db is None and now - _cache["at"] < _CACHE_SECONDS:
        return _cache["value"]
    try:
        own = db is None
        session = SessionLocal() if own else db
        try:
            row = session.get(AppSetting, KEY)
            value = (row.value or {}).get("provider") if row else None
        finally:
            if own:
                session.close()
    except Exception:
        return _cache["value"] if _cache["at"] else None
    value = value if value in PROVIDERS else None
    _cache.update(value=value, at=now)
    return value


def effective_order(db=None) -> List[str]:
    """Providers to try: the administrator's choice first (if its key is configured), then the .env order."""
    base = settings.provider_order
    primary = stored_primary(db)
    if primary and settings._chat_configured(primary):
        rest = [p for p in base if p != primary]
        # Every other configured provider stays available as a fallback.
        rest += [p for p in PROVIDERS if p not in rest and p != primary and settings._chat_configured(p)]
        return [primary] + rest
    return base


def set_primary(db, provider: Optional[str], user_email: str) -> None:
    row = db.get(AppSetting, KEY)
    value = {"provider": provider}
    if row is None:
        db.add(AppSetting(key=KEY, value=value, updated_by=user_email))
    else:
        row.value = value
        row.updated_by = user_email
    db.commit()
    _cache.update(value=provider, at=time.monotonic())
