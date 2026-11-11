import asyncio
import time
import uuid
from fastapi import Depends, FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.core.config import settings
from app.core.database import engine, Base, SessionLocal
import app.models  # noqa: F401 - registers all SQLAlchemy models
from app.services.auth_service import auth_service
from app.services.audit_service import audit_service
from app.core.logging_config import logger, current_request_id
from app.api import (
    health_router,
    ai_router,
    documents_router,
    search_router,
    responses_router,
    calculations_router,
    auth_router,
    audit_router,
    generator_router
)
from app.api.auth import get_current_user


from sqlalchemy import inspect, text


def init_db():
    if engine.dialect.name == "postgresql":
        with engine.begin() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))

    Base.metadata.create_all(bind=engine)
    # Safe schema migration check for existing PostgreSQL instances.
    with engine.begin() as conn:
        inspector = inspect(conn)
        if "documents" in inspector.get_table_names():
            cols = [c["name"] for c in inspector.get_columns("documents")]
            if "is_archived" not in cols:
                conn.execute(text("ALTER TABLE documents ADD COLUMN is_archived BOOLEAN DEFAULT FALSE;"))
            if "archived_at" not in cols:
                conn.execute(text("ALTER TABLE documents ADD COLUMN archived_at TIMESTAMP;"))
        if "prompt_history" in inspector.get_table_names():
            prompt_cols = [c["name"] for c in inspector.get_columns("prompt_history")]
            history_migrations = {
                "session_id": "VARCHAR(100)",
                "turn_index": "INTEGER NOT NULL DEFAULT 1",
                "parent_prompt_id": "UUID",
                "explanation": "TEXT",
                "response_summary": "JSON",
                "full_result": "JSON"
            }
            for column, definition in history_migrations.items():
                if column not in prompt_cols:
                    conn.execute(text(f"ALTER TABLE prompt_history ADD COLUMN {column} {definition};"))

    with SessionLocal() as db:
        auth_service.bootstrap_initial_admin(db)



@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        init_db()
    except Exception as e:
        logger.error(f"[Lifespan Error] Database initialization failed during startup: {e}")
    # Enforce statutory 3-Year audit log retention policy (1,095 days)
    try:
        with SessionLocal() as db:
            purged = audit_service.purge_expired_logs(db, retention_days=1095)
            if purged > 0:
                logger.info(f"[Audit Retention] Automatically purged {purged} expired audit logs older than 3 years (1,095 days).")
    except Exception as e:
        logger.warning(f"[Audit Retention Warning] Could not run statutory log purge: {e}")
    yield


app = FastAPI(
    title=settings.APP_NAME,
    description=(
        "Backend POC for Infosys Social Value RFP Response Builder.\n"
        "Features:\n"
        "- Document ingestion (PDF, DOCX, XLSX)\n"
        "- Text extraction, normalization, and chunking\n"
        "- OpenAI embeddings & PostgreSQL pgvector vector search\n"
        "- Grounded RAG response generation (Core, Enhanced, Localised packages)\n"
        "- Deterministic National TOMs Social Value calculation engine\n"
        "- Enterprise Role-Based Access Control (RBAC) & JWT Auth\n"
        "- Auditable math & non-hallucination guardrails"
    ),
    version="1.0.0",
    lifespan=lifespan
)

# CORS configuration (supports local and deployed origins with credentials)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()],
    allow_origin_regex=settings.CORS_ORIGIN_REGEX or None,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
    expose_headers=["X-Request-ID", "Content-Disposition"],
)


def _persist_audit_record(audit_kwargs: dict) -> None:
    try:
        with SessionLocal() as db:
            audit_service.record_log(db=db, **audit_kwargs)
    except Exception as log_err:
        logger.error(f"Could not persist audit record: {log_err}")


@app.middleware("http")
async def audit_logging_middleware(request: Request, call_next):
    """
    Enterprise Audit & Request ID Tracking Middleware:
    1. Injects/generates unique X-Request-ID.
    2. Logs every API transaction with duration to rotating logs/app.log.
    3. Persists error transactions (status >= 400 or exceptions) to system_audit_logs table.
    """
    request_id = request.headers.get("X-Request-ID") or f"req_{uuid.uuid4().hex[:8]}"
    token = current_request_id.set(request_id)
    start_time = time.time()
    client_ip = request.client.host if request.client else "unknown"

    status_code = 500
    error_msg = None
    try:
        response: Response = await call_next(request)
        status_code = response.status_code
        response.headers["X-Request-ID"] = request_id
        return response
    except Exception as ex:
        error_msg = str(ex)
        logger.exception(f"Unhandled server error on {request.method} {request.url.path}: {ex}")
        raise
    finally:
        duration_ms = round((time.time() - start_time) * 1000, 2)
        current_request_id.reset(token)

        path = request.url.path
        if not path.startswith(("/docs", "/openapi.json", "/favicon")):
            if status_code >= 400 or error_msg:
                logger.warning(
                    f"{request.method} {path} - {status_code} ({duration_ms}ms) | IP: {client_ip} | Error: {error_msg or 'HTTP Error'}"
                )
                audit_kwargs = dict(
                    request_id=request_id,
                    message=f"{request.method} {path} returned HTTP {status_code}",
                    event_type="ERROR_EXCEPTION" if error_msg else "API_ERROR",
                    severity="ERROR" if status_code >= 500 else "WARNING",
                    endpoint=path,
                    method=request.method,
                    status_code=status_code,
                    duration_ms=duration_ms,
                    client_ip=client_ip,
                    error_detail=error_msg,
                )
                # The DB write is blocking (remote Postgres round-trips take seconds);
                # run it in a worker thread so it never stalls the async event loop.
                asyncio.get_running_loop().run_in_executor(None, _persist_audit_record, audit_kwargs)
            else:
                logger.info(f"{request.method} {path} - {status_code} ({duration_ms}ms) | IP: {client_ip}")


# Register API Routers
# Public: health checks and the auth endpoints themselves (login/register/status/me).
app.include_router(health_router)
app.include_router(auth_router)

# Protected: every other router requires a valid Bearer token.
_require_user = [Depends(get_current_user)]
app.include_router(audit_router, dependencies=_require_user)
app.include_router(ai_router, dependencies=_require_user)
app.include_router(documents_router, dependencies=_require_user)
app.include_router(search_router, dependencies=_require_user)
app.include_router(responses_router, dependencies=_require_user)
app.include_router(calculations_router, dependencies=_require_user)
app.include_router(generator_router, dependencies=_require_user)


@app.get("/")
def root():
    return {
        "message": f"Welcome to {settings.APP_NAME}",
        "docs_url": "/docs",
        "health_check": "/health"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=settings.APP_PORT, reload=True)
