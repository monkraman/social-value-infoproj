import uuid
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select
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
        """
        Embeds the query and performs pgvector cosine similarity search
        against stored document chunks.
        """
        query_vector = embedding_service.get_embedding(query)

        # Build distance expression using pgvector cosine_distance (<=> operator)
        distance_expr = DocumentChunk.embedding.cosine_distance(query_vector)

        stmt = (
            select(
                DocumentChunk,
                Document.filename,
                distance_expr.label("distance")
            )
            .join(Document, DocumentChunk.document_id == Document.id)
        )

        if document_id:
            try:
                doc_uuid = uuid.UUID(document_id)
                stmt = stmt.where(DocumentChunk.document_id == doc_uuid)
            except ValueError:
                pass

        # Order by closest distance (smallest cosine distance = highest similarity)
        stmt = stmt.order_by(distance_expr.asc()).limit(top_k)

        results = db.execute(stmt).all()

        search_items = []
        for chunk, filename, distance in results:
            # Cosine similarity is 1.0 - cosine_distance
            similarity = round(max(0.0, min(1.0, 1.0 - float(distance))), 4) if distance is not None else 0.0

            search_items.append(
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

        return search_items


retrieval_service = RetrievalService()
