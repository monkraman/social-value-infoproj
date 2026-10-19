from typing import Generator
from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker, Session

from app.core.config import settings


db_url = settings.DATABASE_URL.strip()
if db_url.startswith("postgresql://"):
    db_url = db_url.replace("postgresql://", "postgresql+psycopg://", 1)
elif db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql+psycopg://", 1)
elif not db_url.startswith("postgresql+psycopg://"):
    raise RuntimeError(
        "DATABASE_URL must point to PostgreSQL using the psycopg driver. "
        "SQLite and other database engines are not supported."
    )

engine = create_engine(
    db_url,
    echo=False,
    pool_pre_ping=True,
    connect_args={"connect_timeout": 10}
)

try:
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
except Exception as exc:
    engine.dispose()
    raise RuntimeError(
        "PostgreSQL is unavailable. The application will not start without its configured PostgreSQL database; "
        "no fallback database is used."
    ) from exc

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
