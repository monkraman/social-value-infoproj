"""
Knowledge Base Seeding Script
Ingests all synthetic documents in documents/synthetic/ and docs/ into PostgreSQL with pgvector.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import SessionLocal
from app.services.document_service import document_service


def seed_knowledge_base():
    db = SessionLocal()
    try:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        folders_to_check = [
            os.path.join(base_dir, "documents", "synthetic"),
            os.path.join(base_dir, "docs")
        ]

        total_ingested = 0
        total_chunks = 0

        for folder in folders_to_check:
            if not os.path.exists(folder):
                continue

            for fname in os.listdir(folder):
                if fname.startswith("~$") or fname.startswith("."):
                    continue
                ext = fname.lower().split(".")[-1]
                if ext in ["pdf", "docx", "xlsx", "txt", "md"]:
                    filepath = os.path.join(folder, fname)
                    print(f"Ingesting: {fname}...")
                    with open(filepath, "rb") as f:
                        file_bytes = f.read()

                    doc = document_service.ingest_document(
                        db=db,
                        file_bytes=file_bytes,
                        filename=fname,
                        custom_metadata={"seeded": True, "source_folder": os.path.basename(folder)}
                    )
                    chunks = len(doc.chunks)
                    total_ingested += 1
                    total_chunks += chunks
                    print(f" -> Ingested {fname} (ID: {doc.id}, {chunks} chunks)")

        print(f"\nSeeding complete: Ingested {total_ingested} documents with {total_chunks} total chunks into pgvector.")
    finally:
        db.close()


if __name__ == "__main__":
    seed_knowledge_base()
