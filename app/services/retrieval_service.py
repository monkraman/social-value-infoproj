import uuid
import numpy as np
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.core.database import IS_POSTGRES
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
        Embeds the query and performs cosine similarity search
        against stored document chunks (via pgvector on PostgreSQL or NumPy on SQLite).
        """
        query_vector = embedding_service.get_embedding(query)

        if IS_POSTGRES:
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

            stmt = stmt.order_by(distance_expr.asc()).limit(top_k)
            results = db.execute(stmt).all()

            search_items = []
            for chunk, filename, distance in results:
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
        else:
            # High-performance in-memory vector ranking for SQLite
            stmt = select(DocumentChunk, Document.filename).join(Document, DocumentChunk.document_id == Document.id)
            if document_id:
                try:
                    doc_uuid = uuid.UUID(document_id)
                    stmt = stmt.where(DocumentChunk.document_id == doc_uuid)
                except ValueError:
                    pass

            results = db.execute(stmt).all()
            if not results:
                return []

            q_vec = np.array(query_vector, dtype=np.float32)
            q_norm = np.linalg.norm(q_vec)

            scored = []
            for chunk, filename in results:
                emb = chunk.embedding
                if emb is not None:
                    c_vec = np.array(emb, dtype=np.float32)
                    c_norm = np.linalg.norm(c_vec)
                    if q_norm > 0 and c_norm > 0:
                        sim = float(np.dot(q_vec, c_vec) / (q_norm * c_norm))
                        # Cosine similarity range normalized
                        similarity = round(max(0.0, min(1.0, (sim + 1.0) / 2.0 if sim < 0 else sim)), 4)
                    else:
                        similarity = 0.0
                else:
                    similarity = 0.0
                scored.append((similarity, chunk, filename))

            scored.sort(key=lambda x: x[0], reverse=True)
            top_results = scored[:top_k]

            return [
                SearchResultItem(
                    chunk_id=str(chunk.id),
                    document_id=str(chunk.document_id),
                    filename=filename,
                    content=chunk.content,
                    similarity=sim,
                    chunk_index=chunk.chunk_index,
                    metadata=chunk.chunk_metadata or {}
                )
                for sim, chunk, filename in top_results
            ]


retrieval_service = RetrievalService()
