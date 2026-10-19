from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

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


@router.get("/history/{prompt_id}")
def get_single_prompt_history(
    prompt_id: str,
    db: Session = Depends(get_db)
):
    """Fetches a single past prompt by ID with full result for restoring a session."""
    item = prompt_interpreter_service.get_history_by_id(db=db, prompt_id=prompt_id)
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No prompt history found with id={prompt_id}"
        )
    return item


class RefineRequest(BaseModel):
    feedback: str = Field(..., min_length=1, description="User's refinement feedback text")
    previous_result: Dict[str, Any] = Field(..., description="The previous ResponseGenerationResult dict")
    previous_prompt: str = Field(default="", description="The original prompt that was used")
    session_id: Optional[str] = Field(default=None, description="Session thread ID")
    parent_prompt_id: Optional[str] = Field(default=None, description="ID of the prompt being refined")
    turn_index: int = Field(default=2, description="Which turn in the conversation thread")
    conversation_turns: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="Full conversation history as [{role, content}] pairs for true multi-turn AI memory"
    )


@router.post("/refine", response_model=PromptSubmissionResponse)
def refine_rfp_response(
    body: RefineRequest,
    db: Session = Depends(get_db)
):
    """
    Refines a previous Social Value proposal using full multi-turn context-aware AI.
    Sends the ENTIRE conversation thread (all previous turns, feedback, results)
    to the LLM so it never forgets earlier instructions — true continuous conversation.
    """
    try:
        data = prompt_interpreter_service.refine_with_feedback(
            db=db,
            feedback_text=body.feedback,
            previous_result=body.previous_result,
            previous_prompt=body.previous_prompt,
            session_id=body.session_id,
            parent_prompt_id=body.parent_prompt_id,
            turn_index=body.turn_index,
            conversation_turns=body.conversation_turns
        )
        return data
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Refinement failed: {str(e)}"
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

