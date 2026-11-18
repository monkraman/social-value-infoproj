import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, Column, DateTime, Float, ForeignKey, Integer, String, Uuid

from app.core.database import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


class GeneratorRun(Base):
    """One saved Initiative Generator result. Private to the user who created it."""

    __tablename__ = "generator_runs"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    client = Column(String(255), nullable=True)
    region = Column(String(100), nullable=True)
    framework = Column(String(20), nullable=True)
    contract_value_gbp = Column(Float, nullable=True)
    target_gbp = Column(Float, nullable=True)
    value_gbp = Column(Float, nullable=True)
    initiative_count = Column(Integer, nullable=False, default=0)
    # The screen as the user left it: tender, criteria, initiatives and their edits.
    state = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=_now, nullable=False)
    updated_at = Column(DateTime, default=_now, onupdate=_now, nullable=False, index=True)
