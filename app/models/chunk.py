import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, Text, DateTime, JSON, ForeignKey, Uuid
from sqlalchemy.orm import relationship
from app.core.database import Base, IS_POSTGRES
from app.core.config import settings

if IS_POSTGRES:
    from pgvector.sqlalchemy import Vector
    VectorType = Vector(settings.EMBEDDING_DIMENSION)
else:
    VectorType = JSON


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, index=True)
    document_id = Column(Uuid, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    chunk_index = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    chunk_metadata = Column("metadata", JSON, nullable=True, default=dict)
    embedding = Column(VectorType, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    document = relationship("Document", back_populates="chunks")

    def __repr__(self) -> str:
        return f"<DocumentChunk id={self.id} doc_id={self.document_id} index={self.chunk_index}>"
