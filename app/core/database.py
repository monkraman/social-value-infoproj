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

# Discover connection string from environment, Azure Connection Strings prefixes, or settings
def _find_raw_db_url() -> str:
    # 1. Standard environment variable
    if os.environ.get("DATABASE_URL"):
        return os.environ["DATABASE_URL"]
    
    # 2. Azure Connection Strings (matches POSTGRESQLCONNSTR_* or CUSTOMCONNSTR_*)
    for key, val in os.environ.items():
        if key.startswith(("POSTGRESQLCONNSTR_", "CUSTOMCONNSTR_")):
            return val
            
    # 3. Fallback to settings or empty
    return settings.DATABASE_URL or ""


def _normalize_db_url(raw: str) -> str:
    cleaned = raw.strip().strip("\"'")
    if not cleaned:
        return ""
        
    # If already a PostgreSQL URI format, normalize driver
    if cleaned.startswith("postgresql+psycopg2://"):
        return cleaned.replace("postgresql+psycopg2://", "postgresql+psycopg://", 1)
    if cleaned.startswith("postgresql://"):
        return cleaned.replace("postgresql://", "postgresql+psycopg://", 1)
    if cleaned.startswith("postgres://"):
        return cleaned.replace("postgres://", "postgresql+psycopg://", 1)
    if cleaned.startswith("postgresql+psycopg://"):
        return cleaned

    # Parse semicolon or space-delimited Azure key-value connection strings:
    # e.g. "Server=xyz.postgres.database.azure.com;Database=db;Port=5432;User Id=usr;Password=pwd;"
    # or "host=xyz port=5432 dbname=db user=usr password=pwd sslmode=require"
    delimiter = ";" if ";" in cleaned else " "
    pairs = {}
    for part in cleaned.split(delimiter):
        if "=" in part:
            k, v = part.split("=", 1)
            pairs[k.strip().lower().replace(" ", "").replace("_", "")] = v.strip().strip("\"'")
            
    host = pairs.get("host") or pairs.get("server") or pairs.get("datasource")
    dbname = pairs.get("dbname") or pairs.get("database") or pairs.get("initialcatalog")
    user = pairs.get("user") or pairs.get("username") or pairs.get("userid")
    password = pairs.get("password") or pairs.get("pwd")
    port = pairs.get("port", "5432")
    sslmode = pairs.get("sslmode", "require")
    
    if host and dbname and user and password:
        return f"postgresql+psycopg://{user}:{password}@{host}:{port}/{dbname}?sslmode={sslmode}"
        
    return cleaned


raw_url = _find_raw_db_url()
db_url = _normalize_db_url(raw_url)

if not db_url.startswith("postgresql+psycopg://"):
    prefix_preview = (db_url[:25] + "...") if len(db_url) > 25 else (db_url or "(empty)")
    raise RuntimeError(
        f"DATABASE_URL must be a valid PostgreSQL connection string starting with postgresql+psycopg://. "
        f"Please configure DATABASE_URL in Azure App Service Environment Variables or Connection Strings. "
        f"Received: '{prefix_preview}'"
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
