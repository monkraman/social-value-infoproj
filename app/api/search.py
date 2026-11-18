from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.search import SearchRequest, SearchResponse
from app.services.embedding_service import EmbeddingUnavailable
from app.services.retrieval_service import retrieval_service

router = APIRouter(tags=["Retrieval"])


@router.post("/search", response_model=SearchResponse)
def search_knowledge(request: SearchRequest, db: Session = Depends(get_db)):
    """
    Milestone 6: Vector Retrieval Endpoint.
    Searches document chunks using pgvector cosine similarity.
    Independent testing of RAG retrieval before LLM generation.
    """
    try:
        results = retrieval_service.search_chunks(
            db=db,
            query=request.query,
            top_k=request.top_k,
            document_id=request.document_id
        )

        return SearchResponse(
            query=request.query,
            total_results=len(results),
            results=results
        )
    except EmbeddingUnavailable as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Search is unavailable right now: {e} No results are shown rather than unreliable ones.",
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Vector search failed: {str(e)}"
        )
