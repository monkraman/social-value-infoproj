from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime
from app.core.database import Base


class RegionalPartner(Base):
    __tablename__ = "regional_partners"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    location = Column(String(100), nullable=False, index=True) # e.g. Birmingham, Manchester, London, National
    partner_name = Column(String(255), nullable=False) # e.g. BMet College & West Midlands Apprenticeship Hub
    theme = Column(String(100), nullable=False, index=True) # Work, Planet, Community, Economy, Modern Slavery
    toms_code = Column(String(50), nullable=True) # e.g. NT1, NT8, NT3
    focus_area = Column(String(255), nullable=True) # e.g. Digital Inclusion, Youth Employment
    contact_info = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    is_approved = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

