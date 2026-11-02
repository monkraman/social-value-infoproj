from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Text, Boolean, DateTime
from app.core.database import Base


class TomsMetric(Base):
    __tablename__ = "toms_metrics"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    code = Column(String(50), unique=True, index=True, nullable=False)
    name = Column(String(255), nullable=False)
    theme = Column(String(100), nullable=False, index=True)
    outcome = Column(String(255), nullable=True)
    unit = Column(String(100), nullable=False)
    unit_value_gbp = Column(Float, nullable=False, default=0.0)
    description = Column(Text, nullable=True)
    evidence_required = Column(Text, nullable=True)
    ppn_mapping = Column(String(100), nullable=True, index=True)
    source = Column(String(100), default="National TOMs / NHS Benchmark")
    is_synthetic = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
