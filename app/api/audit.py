import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, ConfigDict

from app.core.database import get_db
from app.services.audit_service import audit_service

router = APIRouter(prefix="/audit", tags=["Audit & Error Logs"])


class AuditLogItemResponse(BaseModel):
    id: uuid.UUID
    request_id: str
    timestamp: datetime
    event_type: str
    severity: str
    endpoint: Optional[str] = None
    method: Optional[str] = None
    status_code: Optional[int] = None
    duration_ms: Optional[float] = None
    message: str
    error_detail: Optional[str] = None
    client_ip: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)


class AuditSummaryResponse(BaseModel):
    total_logs: int
    total_errors: int
    errors_last_24h: int
    total_warnings: int
    retention_policy: str
    retention_days: int
    oldest_record_timestamp: Optional[str] = None
    system_health: str


@router.get("/logs", response_model=List[AuditLogItemResponse])
def get_system_audit_logs(
    severity: Optional[str] = Query(None, description="Filter by severity: INFO, WARNING, ERROR, CRITICAL"),
    event_type: Optional[str] = Query(None, description="Filter by event type: API_REQUEST, ERROR_EXCEPTION, TENDER_GEN"),
    limit: int = Query(50, ge=1, le=200, description="Max logs to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    db: Session = Depends(get_db)
):
    """
    Returns system audit & error logs.
    Allows administrators to audit system events, track failures, and inspect request latency.
    """
    return audit_service.get_recent_logs(
        db=db,
        severity=severity,
        event_type=event_type,
        limit=limit,
        offset=offset
    )


@router.get("/summary", response_model=AuditSummaryResponse)
def get_audit_summary(db: Session = Depends(get_db)):
    """
    Returns an aggregated summary of error events, total API requests,
    and the 3-Year statutory retention compliance status.
    """
    return audit_service.get_audit_summary(db=db)


@router.post("/purge-expired", status_code=status.HTTP_200_OK)
def purge_expired_audit_logs(
    retention_days: int = Query(1095, description="Retention ceiling in days (default 1095 = 3 years)"),
    db: Session = Depends(get_db)
):
    """
    Enforces the 3-Year statutory retention policy by purging audit log records
    older than retention_days (default 3 years / 1095 days).
    """
    purged_count = audit_service.purge_expired_logs(db=db, retention_days=retention_days)
    return {
        "message": f"Successfully enforced 3-year statutory retention policy.",
        "records_purged": purged_count,
        "retention_days": retention_days
    }
