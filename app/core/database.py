from typing import Generator
from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from app.core.config import settings

# Engine configuration
engine = create_engine(
    settings.DATABASE_URL,
    echo=False,
    pool_pre_ping=True
)

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
    """Verifies PostgreSQL connection and pgvector extension status."""
    try:
        with engine.connect() as conn:
            version_row = conn.execute(text("SELECT version();")).fetchone()
            ext_row = conn.execute(
                text("SELECT extname, extversion FROM pg_extension WHERE extname = 'vector';")
            ).fetchone()

            return {
                "connected": True,
                "postgres_version": version_row[0] if version_row else "Unknown",
                "pgvector_installed": bool(ext_row),
                "pgvector_version": ext_row[1] if ext_row else None
            }
    except Exception as e:
        return {
            "connected": False,
            "error": str(e),
            "postgres_version": None,
            "pgvector_installed": False,
            "pgvector_version": None
        }
