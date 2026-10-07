import sys
import os
import uuid

# Ensure project root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import SessionLocal
from app.models.document import Document
from app.models.chunk import DocumentChunk
from app.services.embedding_service import embedding_service


def test_embedding_and_pgvector():
    db = SessionLocal()
    try:
        sample_text = "Birmingham digital inclusion initiative delivering community workshops and refurbished laptops."
        print(f"Generating embedding for sample text: '{sample_text}'...")
        vec = embedding_service.get_embedding(sample_text)
        assert len(vec) == 1536, f"Expected 1536 dimensions, got {len(vec)}"
        print(f"Received vector of dimension: {len(vec)}")

        # Create temporary document
        doc_id = uuid.uuid4()
        doc = Document(
            id=doc_id,
            filename="test_embedding_sample.txt",
            document_type="txt",
            doc_metadata={"test": True}
        )
        db.add(doc)
        db.flush()

        chunk_id = uuid.uuid4()
        chunk = DocumentChunk(
            id=chunk_id,
            document_id=doc_id,
            chunk_index=0,
            content=sample_text,
            chunk_metadata={"test": True},
            embedding=vec
        )
        db.add(chunk)
        db.commit()
        print(f"Successfully stored chunk {chunk_id} in PostgreSQL document_chunks table with pgvector!")

        # Query back using pgvector distance
        retrieved_chunk = db.query(DocumentChunk).filter(DocumentChunk.id == chunk_id).first()
        assert retrieved_chunk is not None
        print(f"Retrieved chunk content: {retrieved_chunk.content}")

        # Clean up test record
        db.delete(doc)
        db.commit()
        print("Cleaned up test document and chunk.")
        print("Milestone 4 test PASSED!")
    finally:
        db.close()


if __name__ == "__main__":
    test_embedding_and_pgvector()
