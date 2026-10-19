import uuid
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.document import Document
from app.models.chunk import DocumentChunk
from app.schemas.search import SearchResultItem
from app.services.embedding_service import embedding_service


class RetrievalService:
    def search_chunks(
        self,
        db: Session,
        query: str,
        top_k: int = 5,
        document_id: Optional[str] = None
    ) -> List[SearchResultItem]:
        """Search active document chunks with PostgreSQL pgvector cosine distance."""
        query_vector = embedding_service.get_embedding(query)
        distance_expr = DocumentChunk.embedding.cosine_distance(query_vector)

        stmt = (
            select(DocumentChunk, Document.filename, distance_expr.label("distance"))
            .join(Document, DocumentChunk.document_id == Document.id)
            .where(Document.is_archived == False)
        )
        if document_id:
            try:
                stmt = stmt.where(DocumentChunk.document_id == uuid.UUID(document_id))
            except ValueError:
                return []

        rows = db.execute(stmt.order_by(distance_expr.asc()).limit(top_k * 2)).all()
        items: List[SearchResultItem] = []
        for chunk, filename, distance in rows:
            similarity = round(max(0.0, min(1.0, 1.0 - float(distance))), 4) if distance is not None else 0.0
            if similarity <= 0.01:
                continue
            items.append(
                SearchResultItem(
                    chunk_id=str(chunk.id),
                    document_id=str(chunk.document_id),
                    filename=filename,
                    content=chunk.content,
                    similarity=similarity,
                    chunk_index=chunk.chunk_index,
                    metadata=chunk.chunk_metadata or {}
                )
            )
            if len(items) >= top_k:
                break
        return items


retrieval_service = RetrievalService()
