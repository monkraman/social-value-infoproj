from datetime import datetime, timezone

from sqlalchemy import JSON, Column, DateTime, String

from app.core.database import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


class AppSetting(Base):
    """A setting an administrator can change from the tool. Never holds a secret: keys stay in the
    backend's environment (App Service settings / Key Vault), only choices are stored here."""

    __tablename__ = "app_settings"

    key = Column(String(100), primary_key=True)
    value = Column(JSON, nullable=False)
    updated_by = Column(String(255), nullable=True)
    updated_at = Column(DateTime(timezone=True), default=_now, onupdate=_now, nullable=False)
