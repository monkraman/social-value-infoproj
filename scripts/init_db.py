"""
Database Initialization Script
Ensures the pgvector extension is enabled and creates tables.
"""
import sys
import os

# Ensure project root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.core.database import engine, Base, check_db_connection
from app.models import Document, DocumentChunk


def init_db():
    print("Checking PostgreSQL connection...")
    status = check_db_connection()
    if not status["connected"]:
        print(f"Error connecting to database: {status.get('error')}")
        sys.exit(1)

    print(f"Connected to PostgreSQL: {status['postgres_version']}")

    with engine.begin() as conn:
        print("Ensuring pgvector extension is enabled...")
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))

    print("Creating database tables if not existing...")
    Base.metadata.create_all(bind=engine)

    # Verify tables
    with engine.connect() as conn:
        tables = conn.execute(text(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';"
        )).fetchall()
        table_names = [t[0] for t in tables]
        print(f"Verified tables in public schema: {table_names}")

    print("Database initialization completed successfully!")


if __name__ == "__main__":
    init_db()
