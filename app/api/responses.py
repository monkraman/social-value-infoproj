from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.response import OpportunityRequest, ResponseGenerationResult
from app.services.rag_service import rag_service

router = APIRouter(prefix="/responses", tags=["RAG Response Builder"])


@router.post("/generate", response_model=ResponseGenerationResult)
def generate_rfp_response(
    request: OpportunityRequest,
    db: Session = Depends(get_db)
):
    """
    Milestone 7 & 8: RAG Response Generation with Deterministic Calculations.
    1. Retrieves relevant knowledge chunks via pgvector
    2. Sends context + tender parameters to OpenAI LLM
    3. LLM returns structured initiatives across Core, Enhanced, and Localised packages
    4. Deterministic Calculation Layer computes authoritative Social Value & TOMs impact
    5. Flags assumptions and validation_required without hallucinating unsupported partners/costs.
    """
    try:
        result = rag_service.generate_response(db=db, req=request)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Response generation failed: {str(e)}"
        )
