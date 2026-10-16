import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, JSON, Text, Uuid, Boolean, Float, Integer
from app.core.database import Base


class PromptHistory(Base):
    __tablename__ = "prompt_history"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, index=True)
    raw_prompt = Column(Text, nullable=False)
    intent = Column(String(50), nullable=False, default="rfp_opportunity")
    is_rfp_prompt = Column(Boolean, default=True, nullable=False)
    client_name = Column(String(255), nullable=True)
    location = Column(String(100), nullable=True)
    contract_value_gbp = Column(Float, nullable=True)
    contract_duration_years = Column(Integer, nullable=True)
    social_value_weighting_percent = Column(Float, nullable=True)
    priorities = Column(JSON, nullable=True)
    explanation = Column(Text, nullable=True)
    response_summary = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    def __repr__(self) -> str:
        return f"<PromptHistory id={self.id} is_rfp={self.is_rfp_prompt} client={self.client_name}>"
