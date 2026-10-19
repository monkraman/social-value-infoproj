import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from app.models.audit_log import SystemAuditLog
from app.core.logging_config import logger


class AuditService:
    """
    Enterprise Audit Service for managing system logs, error events,
    and enforcing the 3-Year statutory retention policy (1095 days).
    """

    RETENTION_DAYS = 1095  # 3 Years

    @staticmethod
    def record_log(
        db: Session,
        request_id: str,
        message: str,
        event_type: str = "API_REQUEST",
        severity: str = "INFO",
        endpoint: Optional[str] = None,
        method: Optional[str] = None,
        status_code: Optional[int] = None,
        duration_ms: Optional[float] = None,
        user_id: Optional[str] = None,
        client_ip: Optional[str] = None,
        error_detail: Optional[str] = None,
        metadata_payload: Optional[Dict[str, Any]] = None,
    ) -> Optional[SystemAuditLog]:
        try:
            log_entry = SystemAuditLog(
                request_id=request_id,
                message=message,
                event_type=event_type,
                severity=severity.upper(),
                endpoint=endpoint,
                method=method,
                status_code=status_code,
                duration_ms=duration_ms,
                user_id=user_id,
                client_ip=client_ip,
                error_detail=error_detail,
                metadata_payload=metadata_payload,
            )
            db.add(log_entry)
            db.commit()
            db.refresh(log_entry)
            return log_entry
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to record system audit log to database: {e}")
            return None

    @staticmethod
    def get_recent_logs(
        db: Session,
        severity: Optional[str] = None,
        event_type: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[SystemAuditLog]:
        query = db.query(SystemAuditLog)
        if severity:
            query = query.filter(SystemAuditLog.severity == severity.upper())
        if event_type:
            query = query.filter(SystemAuditLog.event_type == event_type)
        return query.order_by(desc(SystemAuditLog.timestamp)).offset(offset).limit(limit).all()

    @staticmethod
    def get_audit_summary(db: Session) -> Dict[str, Any]:
        now = datetime.now(timezone.utc)
        one_day_ago = now - timedelta(days=1)
        seven_days_ago = now - timedelta(days=7)

        total_logs = db.query(SystemAuditLog).count()
        total_errors = db.query(SystemAuditLog).filter(SystemAuditLog.severity.in_(["ERROR", "CRITICAL"])).count()
        errors_24h = (
            db.query(SystemAuditLog)
            .filter(SystemAuditLog.severity.in_(["ERROR", "CRITICAL"]))
            .filter(SystemAuditLog.timestamp >= one_day_ago)
            .count()
        )
        total_warnings = db.query(SystemAuditLog).filter(SystemAuditLog.severity == "WARNING").count()

        oldest_record = db.query(SystemAuditLog.timestamp).order_by(SystemAuditLog.timestamp.asc()).first()
        oldest_str = oldest_record[0].isoformat() if oldest_record else None

        return {
            "total_logs": total_logs,
            "total_errors": total_errors,
            "errors_last_24h": errors_24h,
            "total_warnings": total_warnings,
            "retention_policy": "3-Year Statutory Retention (1095 days)",
            "retention_days": AuditService.RETENTION_DAYS,
            "oldest_record_timestamp": oldest_str,
            "system_health": "WARNINGS_PRESENT" if errors_24h > 0 else "HEALTHY"
        }

    @staticmethod
    def purge_expired_logs(db: Session, retention_days: int = RETENTION_DAYS) -> int:
        """Purges any records older than the specified retention window (default 3 years)."""
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=retention_days)
        deleted_count = db.query(SystemAuditLog).filter(SystemAuditLog.timestamp < cutoff_date).delete()
        db.commit()
        if deleted_count > 0:
            logger.info(f"Purged {deleted_count} audit logs older than {retention_days} days (3-year compliance policy)")
        return deleted_count


audit_service = AuditService()
