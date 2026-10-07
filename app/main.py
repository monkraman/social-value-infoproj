from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.core.config import settings
from app.core.database import engine, Base
from app.api import (
    health_router,
    ai_router,
    documents_router,
    search_router,
    responses_router,
    calculations_router
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: ensure tables exist
    try:
        Base.metadata.create_all(bind=engine)
    except Exception as e:
        print(f"[Startup Warning] Could not verify database tables automatically: {e}")
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
        "- Auditable math & non-hallucination guardrails"
    ),
    version="1.0.0",
    lifespan=lifespan
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API Routers
app.include_router(health_router)
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
