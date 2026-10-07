from fastapi import APIRouter
from app.schemas.ai import AITestRequest, AITestResponse
from app.services.openai_service import openai_service

router = APIRouter(prefix="/ai", tags=["AI Connectivity"])


@router.post("/test", response_model=AITestResponse)
def test_ai(request: AITestRequest):
    """
    Milestone 3: OpenAI Connectivity Test.
    Sends prompt to LLM and returns clean JSON response.
    """
    result = openai_service.test_completion(request.prompt)
    return AITestResponse(
        prompt=result["prompt"],
        response=result["response"],
        model=result["model"],
        is_mock=result.get("is_mock", False)
    )
