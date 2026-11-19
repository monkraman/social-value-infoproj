from typing import Any, Dict, List, Optional

import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.knowledge import load_tables
from app.models.chunk import DocumentChunk
from app.models.document import Document
from app.services.document_service import document_service
from app.services.embedding_service import EmbeddingUnavailable
from app.services.generator_service import generate
from app.services.retrieval_service import retrieval_service
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

    # How each past initiative was actually phased, from the contract scorecard. Shown beside
    # "done before" so a bid team can reuse the real sequence; never sent to the AI, so it
    # costs no prompt budget.
    delivery: Dict[str, List[Dict[str, str]]] = {}
    for d in t.get("delivery") or []:
        ini, step = str(d.get("Initiative") or "").strip(), str(d.get("Step") or "").strip()
        if ini and step:
            delivery.setdefault(ini, []).append({
                "step": step, "due": str(d.get("Due") or "").strip(), "cycle": str(d.get("Reporting cycle") or "").strip()
            })

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
        "delivery": delivery,
        "documents": documents,
        "warnings": warnings,
    }


# A passage below this similarity is not shown as evidence: it is more likely noise than support.
EVIDENCE_MIN_SIMILARITY = 0.6
EVIDENCE_PER_INITIATIVE = 2
EVIDENCE_SNIPPET_CHARS = 400


def attach_evidence(result: Dict[str, Any], db: Session) -> None:
    """Passages from the document repository that support each proposed initiative.

    Runs after the AI and the valuation, so evidence never changes what is proposed or valued.
    Leaves every list empty, with a note in `checks`, when nothing is indexed or search is down.
    """
    initiatives = result.get("initiatives") or []
    for ini in initiatives:
        ini["evidence"] = []
    has_docs = db.query(DocumentChunk.id).join(Document).filter(Document.is_archived.is_(False)).first()
    if not has_docs:
        result["checks"].append("No past bid documents in the repository yet, so no supporting evidence is shown.")
        return
    try:
        # Each passage goes to the one initiative it matches best, so a generic paragraph is not
        # repeated under every card as if it supported all of them.
        best: Dict[str, tuple] = {}  # chunk id -> (similarity, initiative index, hit)
        for idx, ini in enumerate(initiatives):
            query = f"{ini.get('name') or ''}. {ini.get('description') or ''}"
            for h in retrieval_service.search_chunks(db=db, query=query, top_k=EVIDENCE_PER_INITIATIVE * 3):
                if h.similarity >= EVIDENCE_MIN_SIMILARITY and h.similarity > best.get(h.chunk_id, (0.0,))[0]:
                    best[h.chunk_id] = (h.similarity, idx, h)
        for similarity, idx, h in sorted(best.values(), key=lambda b: -b[0]):
            ini = initiatives[idx]
            if len(ini["evidence"]) >= EVIDENCE_PER_INITIATIVE or any(e["document_id"] == h.document_id for e in ini["evidence"]):
                continue  # at most one passage per document per initiative keeps the list readable
            text = " ".join(h.content.split())
            ini["evidence"].append({
                "document_id": h.document_id,
                "filename": h.filename,
                "kind": _kind(h.filename),
                "snippet": text[:EVIDENCE_SNIPPET_CHARS] + ("…" if len(text) > EVIDENCE_SNIPPET_CHARS else ""),
                "similarity": similarity,
            })
    except EmbeddingUnavailable as e:
        for ini in initiatives:
            ini["evidence"] = []
        result["checks"].append(f"Evidence search is unavailable right now ({e}); no supporting evidence is shown.")


@router.post("/run")
def run_generator(req: GeneratorRequest, db: Session = Depends(get_db)):
    if req.region not in {r["region"] for r in load_tables()["regions"]}:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=f"Unknown region '{req.region}'")
    try:
        result = generate(TenderForm(**req.model_dump()))
    except LLMUnavailable as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=f"AI unavailable: {e}") from e
    attach_evidence(result, db)
    return result


# Policy and tender documents are read for the generator, never stored by these two endpoints.
EXTRACT_MAX_BYTES = 15 * 1024 * 1024
EXTRACT_MAX_CHARS = 400_000


@router.post("/extract")
def extract_text(file: UploadFile = File(...)) -> Dict[str, str]:
    """Text of an uploaded PDF, Word, Excel, TXT or MD file. The file is read and discarded."""
    name = file.filename or "document"
    data = file.file.read(EXTRACT_MAX_BYTES + 1)
    if not data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="The file is empty.")
    if len(data) > EXTRACT_MAX_BYTES:
        raise HTTPException(status_code=status.HTTP_413_CONTENT_TOO_LARGE, detail="The file is larger than 15 MB.")
    try:
        text = document_service.extract_full_text(data, name)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                            detail=f"Could not read {name}. Is it a valid, unprotected file?") from e
    if not text.strip():
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                            detail=f"No readable text in {name}. A scanned PDF needs OCR first.")
    return {"name": name, "text": text[:EXTRACT_MAX_CHARS]}


@router.get("/documents/{document_id}/text")
def document_text(document_id: str, db: Session = Depends(get_db)) -> Dict[str, str]:
    """Text of a document already in the repository, rebuilt from its indexed passages."""
    try:
        doc_uuid = uuid.UUID(document_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")
    doc = db.query(Document).filter(Document.id == doc_uuid, Document.is_archived.is_(False)).first()
    if doc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")
    chunks = (db.query(DocumentChunk.content).filter(DocumentChunk.document_id == doc_uuid)
              .order_by(DocumentChunk.chunk_index).all())
    return {"name": doc.filename, "text": "\n\n".join(c.content for c in chunks)[:EXTRACT_MAX_CHARS]}
