from typing import Generator
from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker, Session

from app.core.config import settings


import os
import socket

# IPv6 blackhole mitigation: prioritize IPv4 addresses
_orig_getaddrinfo = socket.getaddrinfo
def _ipv4_first_getaddrinfo(*args, **kwargs):
    res = _orig_getaddrinfo(*args, **kwargs)
    ipv4 = [r for r in res if r[0] == socket.AF_INET]
    return ipv4 if ipv4 else res
socket.getaddrinfo = _ipv4_first_getaddrinfo

raw_url = (
    os.environ.get("DATABASE_URL")
    or os.environ.get("POSTGRESQLCONNSTR_DATABASE_URL")
    or os.environ.get("CUSTOMCONNSTR_DATABASE_URL")
    or settings.DATABASE_URL
    or ""
)

db_url = raw_url.strip().strip("\"'")

# Auto-correct common dialect prefixes
if db_url.startswith("postgresql+psycopg2://"):
    db_url = db_url.replace("postgresql+psycopg2://", "postgresql+psycopg://", 1)
elif db_url.startswith("postgresql://"):
    db_url = db_url.replace("postgresql://", "postgresql+psycopg://", 1)
elif db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql+psycopg://", 1)

if not db_url.startswith("postgresql+psycopg://"):
    prefix_preview = (db_url[:20] + "...") if len(db_url) > 20 else (db_url or "(empty)")
    raise RuntimeError(
        f"DATABASE_URL must be a valid PostgreSQL connection string starting with postgresql+psycopg://. "
        f"Please configure DATABASE_URL in Azure App Service Environment Variables or local .env file. "
        f"Received prefix: '{prefix_preview}'"
    )

engine = create_engine(
    db_url,
    echo=False,
    pool_pre_ping=True,
    connect_args={"connect_timeout": 15}
)

try:
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
except Exception as exc:
    print(f"[Database Warning] Initial PostgreSQL connection check could not complete: {exc}")

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """Yield a session connected to the single configured PostgreSQL database."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_db_connection() -> dict:
    """Report PostgreSQL and pgvector availability without switching engines."""
    try:
        with engine.connect() as connection:
            version = connection.execute(text("SELECT version()")).scalar_one()
            vector_version = connection.execute(
                text("SELECT extversion FROM pg_extension WHERE extname = 'vector'")
            ).scalar_one_or_none()
        return {
            "connected": True,
            "engine": "postgresql",
            "postgres_version": version,
            "pgvector_installed": bool(vector_version),
            "pgvector_version": vector_version
        }
    except Exception as exc:
        return {
            "connected": False,
            "engine": "postgresql",
            "error": str(exc),
            "postgres_version": None,
            "pgvector_installed": False,
            "pgvector_version": None
        }
