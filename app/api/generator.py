from typing import List, Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.knowledge import load_tables
from app.services.generator_service import generate
from app.services.initiative_valuation import TenderForm
from app.services.llm_client import LLMUnavailable

router = APIRouter(prefix="/generator", tags=["Initiative Generator"])


class GeneratorRequest(BaseModel):
    company: str = Field(default="Infosys", min_length=1)
    bid_amount_gbp: float = Field(..., gt=0)
    sv_percent: float = Field(..., gt=0, le=100)
    region: str
    duration_years: float = Field(..., gt=0, le=30)
    themes: List[str] = Field(default_factory=list)
    industry: Optional[str] = None


@router.get("/options")
def generator_options():
    """Choices for the form, taken from the tables."""
    t = load_tables()
    themes = list(dict.fromkeys(m["theme"] for m in t["measures"] if m.get("theme")))
    return {
        "regions": [r["region"] for r in t["regions"]],
        "themes": themes,
        "default_region": t["settings"]["default_region"],
        "default_industry": t["settings"]["default_industry"],
        "tables": {"source": t.get("source"), "edition": t.get("edition"), "imported_at": t.get("imported_at")},
    }


@router.post("/run")
def run_generator(req: GeneratorRequest):
    if req.region not in {r["region"] for r in load_tables()["regions"]}:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=f"Unknown region '{req.region}'")
    try:
        return generate(TenderForm(**req.model_dump()))
    except LLMUnavailable as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=f"AI unavailable: {e}") from e
