import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, Column, DateTime, Float, ForeignKey, Integer, String, Uuid

from app.core.database import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


class GeneratorBid(Base):
    """A bid response written in the RFP editor from generated initiatives.

    Saved bids are listed in the Repository for the whole team ("Bids generated from the tool"),
    so past wording can be reused and later fed back into suggestions. Only the author can change
    or delete one.
    """

    __tablename__ = "generator_bids"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    client = Column(String(255), nullable=True)
    framework = Column(String(20), nullable=True)
    status = Column(String(30), nullable=False, default="Draft")
    initiative_count = Column(Integer, nullable=False, default=0)
    value_gbp = Column(Float, nullable=True)
    cost_gbp = Column(Float, nullable=True)
    # The editor's content: blocks of numbered sections, tables and KPIs, as the user left them.
    document = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=_now, nullable=False)
    updated_at = Column(DateTime, default=_now, onupdate=_now, nullable=False, index=True)
