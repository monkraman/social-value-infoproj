from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.core.config import settings
from app.core.database import engine, Base, SessionLocal, IS_POSTGRES
import app.models  # noqa: F401 - registers all SQLAlchemy models
from app.services.auth_service import auth_service
from app.api import (
    health_router,
    ai_router,
    documents_router,
    search_router,
    responses_router,
    calculations_router,
    auth_router
)


from sqlalchemy import inspect, text


def init_db():
    try:
        if IS_POSTGRES:
            try:
                with engine.begin() as conn:
                    conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
            except Exception as ext_err:
                print(f"[Database Warning] Could not ensure pgvector extension: {ext_err}")

        Base.metadata.create_all(bind=engine)
        # Safe schema migration check for existing database instances
        try:
            with engine.begin() as conn:
                inspector = inspect(engine)
                if "documents" in inspector.get_table_names():
                    cols = [c["name"] for c in inspector.get_columns("documents")]
                    if "is_archived" not in cols:
                        conn.execute(text("ALTER TABLE documents ADD COLUMN is_archived BOOLEAN DEFAULT 0;"))
                    if "archived_at" not in cols:
                        conn.execute(text("ALTER TABLE documents ADD COLUMN archived_at TIMESTAMP;"))
        except Exception as mig_err:
            pass

        with SessionLocal() as db:
            auth_service.ensure_default_superadmin(db)
    except Exception as e:
        print(f"[Startup Warning] Could not initialize database/auth automatically: {e}")



# Initialize database schema immediately so test runners and workers have tables ready
init_db()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
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
    allow_origin_regex=r"^https?://.*$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Register API Routers
app.include_router(health_router)
app.include_router(auth_router)
app.include_router(ai_router)
app.include_router(documents_router)
app.include_router(search_router)
app.include_router(responses_router)
app.include_router(calculations_router)


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
