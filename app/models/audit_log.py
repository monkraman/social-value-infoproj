import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, JSON, Text, Uuid, Integer, Float
from app.core.database import Base


class SystemAuditLog(Base):
    """
    Enterprise System Audit & Error Log Table.
    Maintains full audit trails of API requests, system errors, and RAG operations.
    Supports 3-year statutory compliance retention (PPN 06/20 & Public Contracts Regulations).
    """
    __tablename__ = "system_audit_logs"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, index=True)
    request_id = Column(String(64), index=True, nullable=False)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True, nullable=False)
    event_type = Column(String(50), default="API_REQUEST", index=True, nullable=False)
    severity = Column(String(20), default="INFO", index=True, nullable=False)  # INFO, WARNING, ERROR, CRITICAL
    endpoint = Column(String(255), nullable=True)
    method = Column(String(10), nullable=True)
    status_code = Column(Integer, nullable=True)
    duration_ms = Column(Float, nullable=True)
    user_id = Column(String(100), nullable=True, index=True)
    client_ip = Column(String(50), nullable=True)
    message = Column(Text, nullable=False)
    error_detail = Column(Text, nullable=True)
    metadata_payload = Column(JSON, nullable=True)

    def __repr__(self) -> str:
        return f"<SystemAuditLog id={self.id} req={self.request_id} sev={self.severity} ep={self.endpoint} status={self.status_code}>"
