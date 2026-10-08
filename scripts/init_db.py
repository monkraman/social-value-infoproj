"""
Database Initialization Script
Ensures tables exist and pgvector is enabled if on PostgreSQL.
"""
import sys
import os

# Ensure project root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text, inspect
from app.core.database import engine, Base, check_db_connection, IS_POSTGRES
from app.models import Document, DocumentChunk


def init_db():
    print("Checking Database connection...")
    status = check_db_connection()
    if not status["connected"]:
        print(f"Error connecting to database: {status.get('error')}")
        sys.exit(1)

    print(f"Connected to Database: {status.get('postgres_version') or status.get('engine')}")

    if IS_POSTGRES:
        with engine.begin() as conn:
            print("Ensuring pgvector extension is enabled...")
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))

    print("Creating database tables if not existing...")
    Base.metadata.create_all(bind=engine)

    # Verify tables
    inspector = inspect(engine)
    table_names = inspector.get_table_names()
    print(f"Verified tables in database: {table_names}")

    print("Database initialization completed successfully!")


if __name__ == "__main__":
    init_db()
