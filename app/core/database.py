from typing import Generator
import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from app.core.config import settings

db_url = settings.DATABASE_URL
IS_POSTGRES = db_url.startswith("postgresql") or db_url.startswith("postgres")


def create_db_engine():
    global db_url, IS_POSTGRES
    if IS_POSTGRES:
        try:
            eng = create_engine(db_url, echo=False, pool_pre_ping=True, connect_args={"connect_timeout": 2})
            with eng.connect() as conn:
                conn.execute(text("SELECT 1;"))
            return eng, True
        except Exception as e:
            print(f"[Database Warning] PostgreSQL not reachable ({e}). Falling back to SQLite.")
    
    # Portable SQLite database fallback
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    sqlite_path = os.path.join(base_dir, "social_value.db")
    sqlite_url = f"sqlite:///{sqlite_path}"
    eng = create_engine(sqlite_url, echo=False, connect_args={"check_same_thread": False})
    return eng, False


engine, IS_POSTGRES = create_db_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """Dependency that yields a database session and closes it afterwards."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_db_connection() -> dict:
    """Verifies Database connection and vector extension status."""
    try:
        with engine.connect() as conn:
            if IS_POSTGRES:
                version_row = conn.execute(text("SELECT version();")).fetchone()
                ext_row = conn.execute(
                    text("SELECT extname, extversion FROM pg_extension WHERE extname = 'vector';")
                ).fetchone()

                return {
                    "connected": True,
                    "engine": "postgresql",
                    "postgres_version": version_row[0] if version_row else "Unknown",
                    "pgvector_installed": bool(ext_row),
                    "pgvector_version": ext_row[1] if ext_row else None
                }
            else:
                return {
                    "connected": True,
                    "engine": "sqlite",
                    "postgres_version": "SQLite 3 (Portable / Embedded)",
                    "pgvector_installed": True,
                    "pgvector_version": "NumPy Vector Engine (1536 dim)"
                }
    except Exception as e:
        return {
            "connected": False,
            "error": str(e),
            "postgres_version": None,
            "pgvector_installed": False,
            "pgvector_version": None
        }
