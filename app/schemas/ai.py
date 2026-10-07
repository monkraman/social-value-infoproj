from typing import Optional
from pydantic import BaseModel, Field


class AITestRequest(BaseModel):
    prompt: str = Field(..., description="Prompt to send to the LLM", examples=["Explain Social Value in one sentence."])


class AITestResponse(BaseModel):
    prompt: str
    response: str
    model: str
    is_mock: bool = False
