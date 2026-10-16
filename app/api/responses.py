from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.response import (
    OpportunityRequest,
    ResponseGenerationResult,
    PromptSubmissionRequest,
    PromptSubmissionResponse,
    PromptHistoryItem
)
from app.services.rag_service import rag_service
from app.services.prompt_interpreter_service import prompt_interpreter_service

router = APIRouter(prefix="/responses", tags=["RAG Response Builder"])


@router.post("/prompt", response_model=PromptSubmissionResponse)
def submit_natural_language_prompt(
    submission: PromptSubmissionRequest,
    db: Session = Depends(get_db)
):
    """
    Submits a natural language tender prompt directly to the backend.
    The backend AI/NLP:
    1. Interprets user intent (valid tender specification vs general/non-RFP chatter)
    2. Extracts all parameters (duration, value, weighting, client, location, priorities)
    3. Records the prompt in the persistent audit history table
    4. Executes the RAG generation pipeline and saves the response snapshot
    5. Returns structured packages or guidance if invalid.
    """
    try:
        data = prompt_interpreter_service.interpret_and_execute(
            db=db,
            prompt_text=submission.prompt,
            user_id=submission.user_id
        )
        return data
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Prompt interpretation failed: {str(e)}"
        )


@router.get("/history", response_model=List[PromptHistoryItem])
def get_prompt_history(
    limit: int = 25,
    db: Session = Depends(get_db)
):
    """Returns chronologically ordered history of user submitted prompts and responses."""
    try:
        return prompt_interpreter_service.list_history(db=db, limit=limit)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve prompt history: {str(e)}"
        )


@router.post("/generate", response_model=ResponseGenerationResult)
def generate_rfp_response(
    request: OpportunityRequest,
    db: Session = Depends(get_db)
):
    """
    Milestone 7 & 8: Structured RAG Response Generation with Deterministic Calculations.
    1. Retrieves relevant knowledge chunks via pgvector
    2. Sends context + tender parameters to LLM
    3. Returns structured initiatives across Core, Enhanced, and Localised packages
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

