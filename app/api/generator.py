from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.knowledge import load_tables
from app.models.document import Document
from app.services.generator_service import generate
from app.services.initiative_valuation import TenderForm
from app.services.llm_client import LLMUnavailable
from app.services.tender_prompt import parse_tender_prompt

router = APIRouter(prefix="/generator", tags=["Initiative Generator"])

# Filename hints -> the kinds the generator's policy pickers offer.
DOCUMENT_KINDS = (
    ("past-response", ("response", "submission", "questionnaire", "tender")),
    ("feedback", ("feedback", "outcome", "debrief")),
    ("contract", ("schedule", "contract", "ccn")),
    ("policy", ("policy", "strategy")),
    ("framework", ("ppn", "social-value-model", "social value model")),
    ("guide", ("guide", "glossary", "quick reference")),
)


def _kind(filename: str) -> str:
    lower = (filename or "").lower()
    for kind, hints in DOCUMENT_KINDS:
        if any(h in lower for h in hints):
            return kind
    return "other"


class GeneratorRequest(BaseModel):
    company: str = Field(default="Infosys", min_length=1)
    bid_amount_gbp: float = Field(..., gt=0)
    sv_percent: float = Field(..., gt=0, le=100)
    region: str
    duration_years: float = Field(..., gt=0, le=30)
    themes: List[str] = Field(default_factory=list)
    industry: Optional[str] = None
    client: Optional[str] = None
    framework: Optional[str] = Field(default=None, pattern=r"^(PPN0620|PPN002|PPN026)$")
    brief: Optional[str] = Field(default=None, max_length=5000)


class ParseRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=5000)


@router.post("/parse")
def parse_prompt(req: ParseRequest):
    """Fill the form from a plain-English tender description. No AI; reports what was not found."""
    return parse_tender_prompt(req.text, load_tables())


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


@router.get("/knowledge")
def generator_knowledge(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Everything the Initiative Generator needs, in the shape the frontend already uses.

    This is the team's source of truth. It replaces the dev-only local folder reader, so the
    same screens work from a deployed build — the folder stays a convenience for local work.
    """
    t = load_tables()
    contract = str(t["settings"].get("contract") or "")

    measures = [{
        "code": m["code"], "theme": m.get("theme") or "", "outcome": m.get("outcome") or "",
        "name": m.get("name") or "", "unit": m.get("unit") or "", "proxy_gbp": m.get("proxy_gbp"),
        "proxy_year": 2025, "source": t.get("edition") or "", "definition": m.get("definition") or "",
        "unit_guidance": m.get("unit_guidance") or "", "target_guidance": m.get("target_guidance") or "",
        "evidence_required": "", "localised": bool(m.get("localised")),
    } for m in t["measures"]]

    measure_mac = [{
        "code": str(r.get("Measure code") or ""), "framework_version": str(r.get("Framework version") or ""),
        "mac": str(r.get("MAC") or ""), "strength": str(r.get("Strength") or ""),
        "serves": str(r.get("Criterion it serves") or ""), "note": str(r.get("Why") or ""),
    } for r in (t.get("measure_mac") or [])]

    track_record = [{
        "id": str(i.get("id") or ""), "name": i.get("name") or "", "what": i.get("what") or "",
        "volume": str(i.get("volume") or ""), "mac": str(i.get("mac") or "").replace("MAC ", ""),
        "pillar": i.get("pillar") or "", "delivered_by": i.get("delivered_by") or "",
        "measures": [c for c in (i.get("measures") or []) if str(c).upper().startswith("NT")],
        "contract": contract,
    } for i in t["initiative_library"] if i.get("id")]

    documents = [{
        "path": str(d.id), "name": d.filename, "kind": _kind(d.filename),
        "modified": d.created_at.isoformat() if d.created_at else "", "size": 0,
    } for d in db.query(Document).filter(Document.is_archived.is_(False)).order_by(Document.filename).all()]

    # Who Infosys has actually worked with, so a suggested partner can be weighed against
    # the ones already used rather than accepted on the AI's word.
    partners = [{
        "name": str(c.get("Partner") or ""), "capability": str(c.get("Capability") or ""),
        "worked_with_before": str(c.get("Proven") or "").startswith("Delivered"),
        "contract_specific": str(c.get("Available") or "").startswith("This contract"),
        "note": str(c.get("Notes") or ""),
    } for c in (t.get("capability") or []) if str(c.get("Partner") or "").strip()]

    warnings: List[str] = []
    if not measure_mac:
        warnings.append("Measure-MAC map not loaded: criteria shown come from the tool's draft mapping.")
    if not contract:
        warnings.append('No contract name in the workbook Settings, so "done before" cannot say where the work was committed.')

    return {
        "connected": True,
        "folder": t.get("source") or "the backend",
        "loaded_at": t.get("imported_at") or "",
        "sources": [{"file": t.get("source") or "", "modified": t.get("imported_at") or "", "used_for": "Measures, localisation, criteria map and the Infosys track record"}],
        "measures": measures,
        "regions": t["regions"],
        "industries": t["industries"],
        "patterns": t.get("patterns") or [],
        "measure_mac": measure_mac,
        "track_record": track_record,
        "partners": partners,
        "documents": documents,
        "warnings": warnings,
    }


@router.post("/run")
def run_generator(req: GeneratorRequest):
    if req.region not in {r["region"] for r in load_tables()["regions"]}:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=f"Unknown region '{req.region}'")
    try:
        return generate(TenderForm(**req.model_dump()))
    except LLMUnavailable as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=f"AI unavailable: {e}") from e
