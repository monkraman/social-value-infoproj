"""Bid responses written in the RFP editor, and their Word export.

A saved bid is visible to the whole team in the Repository under "Bids generated from the tool",
so wording that went into one bid can be found and reused in the next. Only its author can
change or delete it. The Word file follows the layout of Schedule 8 (Supplier Solution, Annex 6 –
Social Value): numbered sections per commitment, lettered lists, a commitments table, and the
performance indicators in the style of Schedule 3b.
"""
import io
import json
import re
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from docx import Document as WordDocument
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls
from docx.shared import Pt, RGBColor
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.core.database import get_db
from app.models.generator_bid import GeneratorBid
from app.models.user import User

router = APIRouter(prefix="/generator/bids", tags=["Initiative Generator bids"])

MAX_DOCUMENT_BYTES = 2_000_000


class BidIn(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    client: Optional[str] = Field(default=None, max_length=255)
    framework: Optional[str] = Field(default=None, max_length=20)
    status: str = Field(default="Draft", max_length=30)
    initiative_count: int = Field(default=0, ge=0, le=1000)
    value_gbp: Optional[float] = Field(default=None, ge=0)
    cost_gbp: Optional[float] = Field(default=None, ge=0)
    document: Dict[str, Any]

    @field_validator("title", "client")
    @classmethod
    def _strip(cls, v: Optional[str]) -> Optional[str]:
        return v.strip() or None if v is not None else None

    @field_validator("document")
    @classmethod
    def _size(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        if len(json.dumps(v, default=str)) > MAX_DOCUMENT_BYTES:
            raise ValueError("Bid is too large")
        return v


class BidSummary(BaseModel):
    id: str
    title: str
    client: Optional[str]
    framework: Optional[str]
    status: str
    initiative_count: int
    value_gbp: Optional[float]
    cost_gbp: Optional[float]
    author: str
    mine: bool
    created_at: datetime
    updated_at: datetime


class BidDetail(BidSummary):
    document: Dict[str, Any]


def _summary(bid: GeneratorBid, user: User, db: Session) -> Dict[str, Any]:
    author = db.query(User).filter(User.id == bid.user_id).first()
    return {
        "id": str(bid.id), "title": bid.title, "client": bid.client, "framework": bid.framework,
        "status": bid.status, "initiative_count": bid.initiative_count, "value_gbp": bid.value_gbp,
        "cost_gbp": bid.cost_gbp, "author": author.name if author else "", "mine": bid.user_id == user.id,
        "created_at": bid.created_at, "updated_at": bid.updated_at,
    }


def _bid(bid_id: str, db: Session) -> GeneratorBid:
    try:
        bid = db.query(GeneratorBid).filter(GeneratorBid.id == uuid.UUID(bid_id)).first()
    except ValueError:
        bid = None
    if bid is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bid not found")
    return bid


def _own_bid(bid_id: str, user: User, db: Session) -> GeneratorBid:
    bid = _bid(bid_id, db)
    if bid.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the author can change this bid")
    return bid


def _apply(bid: GeneratorBid, body: BidIn) -> None:
    bid.title, bid.client, bid.framework, bid.status = body.title or "Untitled bid", body.client, body.framework, body.status
    bid.initiative_count, bid.value_gbp, bid.cost_gbp, bid.document = body.initiative_count, body.value_gbp, body.cost_gbp, body.document


@router.get("", response_model=List[BidSummary])
def list_bids(limit: int = Query(100, ge=1, le=500), user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Every saved bid, newest first: the team's library of wording that went into bids."""
    bids = db.query(GeneratorBid).order_by(GeneratorBid.updated_at.desc()).limit(limit).all()
    return [_summary(b, user, db) for b in bids]


@router.post("", response_model=BidSummary, status_code=status.HTTP_201_CREATED)
def create_bid(body: BidIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    bid = GeneratorBid(user_id=user.id)
    _apply(bid, body)
    db.add(bid)
    db.commit()
    db.refresh(bid)
    return _summary(bid, user, db)


@router.get("/{bid_id}", response_model=BidDetail)
def get_bid(bid_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    bid = _bid(bid_id, db)
    return {**_summary(bid, user, db), "document": bid.document}


@router.put("/{bid_id}", response_model=BidSummary)
def update_bid(bid_id: str, body: BidIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    bid = _own_bid(bid_id, user, db)
    _apply(bid, body)
    db.commit()
    db.refresh(bid)
    return _summary(bid, user, db)


@router.delete("/{bid_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_bid(bid_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    bid = _own_bid(bid_id, user, db)
    db.delete(bid)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


class DocxIn(BaseModel):
    document: Dict[str, Any]

    @field_validator("document")
    @classmethod
    def _size(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        if len(json.dumps(v, default=str)) > MAX_DOCUMENT_BYTES:
            raise ValueError("Bid is too large")
        return v


@router.post("/docx")
def export_docx(body: DocxIn):
    """The editor's content as a Word file. Nothing is stored; the file is built and returned."""
    data = render_docx(body.document)
    name = re.sub(r"[^A-Za-z0-9 _-]+", "", str(body.document.get("title") or "Social value response")).strip()[:80] or "Social value response"
    return Response(
        content=data,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{name}.docx"'},
    )


# --- Word layout, after Schedule 8 – Supplier Solution – Annex 6 – Social Value ----------------

INK = RGBColor(0x1A, 0x1A, 0x1A)
HEAD_FILL = "D9E2F3"
FONT = "Arial"


def _run(paragraph, text: str, bold: bool = False, size: float = 10, italic: bool = False):
    r = paragraph.add_run(text)
    r.bold, r.italic = bold, italic
    r.font.name, r.font.size, r.font.color.rgb = FONT, Pt(size), INK
    return r


def _para(doc, number: str, text: str, bold: bool = False, size: float = 10, indent: float = 0):
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(6)
    p.paragraph_format.left_indent = Pt(indent + (36 if number else 0))
    if number:
        p.paragraph_format.first_line_indent = Pt(-36)
        _run(p, f"{number}\t", bold=bold, size=size)
    _run(p, text, bold=bold, size=size)
    return p


def _shade(cell, fill: str) -> None:
    cell._tc.get_or_add_tcPr().append(parse_xml(f'<w:shd {nsdecls("w")} w:fill="{fill}"/>'))


def _table(doc, head: List[str], rows: List[List[str]]) -> None:
    if not head:
        return
    t = doc.add_table(rows=1, cols=len(head))
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, h in enumerate(head):
        cell = t.rows[0].cells[i]
        cell.text = ""
        _run(cell.paragraphs[0], str(h), bold=True, size=9)
        _shade(cell, HEAD_FILL)
    for row in rows:
        cells = t.add_row().cells
        for i in range(len(head)):
            cells[i].text = ""
            _run(cells[i].paragraphs[0], str(row[i]) if i < len(row) and row[i] is not None else "", size=9)
    doc.add_paragraph().paragraph_format.space_after = Pt(2)


def _letters(i: int) -> str:
    return f"({chr(ord('a') + i)})" if i < 26 else f"({i + 1})"


def render_docx(document: Dict[str, Any]) -> bytes:
    doc = WordDocument()
    for s in doc.sections:
        header = s.header.paragraphs[0]
        header.text = ""
        _run(header, "Schedule 8 – Supplier Solution – Annex 6 – Social Value", size=8, italic=True)
    normal = doc.styles["Normal"]
    normal.font.name, normal.font.size = FONT, Pt(10)

    title = str(document.get("title") or "Social value response")
    client = str(document.get("client") or "").strip()
    for text in ("SCHEDULE 8 – SUPPLIER SOLUTION", "ANNEX 6 – SOCIAL VALUE"):
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        _run(p, text, bold=True, size=13)
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    _run(p, title + (f" — {client}" if client else ""), size=10, italic=True)

    intro = [str(x) for x in document.get("introduction") or [] if str(x).strip()]
    _para(doc, "", "SECTION A – DELIVERABLES", bold=True, size=11)
    for text in intro or ["These proposals form the initial Social Value commitments as part of the contract delivery. "
                          "These can be varied to deliver equivalent benefits by mutual agreement."]:
        _para(doc, "", text)

    kpis: List[List[str]] = []
    for n, block in enumerate(document.get("blocks") or [], start=1):
        ref = " / ".join(x for x in (str(block.get("ref") or "").strip(), f"({block['mac']})" if block.get("mac") else "") if x)
        _para(doc, str(n), f"{ref}  {str(block.get('heading') or '').upper()}".strip(), bold=True, size=11)
        k = 0
        for section in block.get("sections") or []:
            k += 1
            _para(doc, f"{n}.{k}", str(section.get("heading") or ""), bold=True)
            for text in section.get("paragraphs") or []:
                if str(text).strip():
                    k += 1
                    _para(doc, f"{n}.{k}", str(text))
            bullets = [str(b) for b in section.get("bullets") or [] if str(b).strip()]
            for i, b in enumerate(bullets):
                _para(doc, _letters(i), b, indent=36)
            table = section.get("table")
            if table and table.get("head"):
                _table(doc, [str(h) for h in table["head"]], [[str(c) for c in r] for r in table.get("rows") or []])
        for kpi in block.get("kpis") or []:
            kpis.append([str(kpi.get(f) or "") for f in ("ref", "indicator", "target", "measure", "cycle")])

    if kpis:
        doc.add_page_break()
        _para(doc, "", "PERFORMANCE INDICATORS (SCHEDULE 3b – ANNEX 1)", bold=True, size=11)
        _para(doc, "", "The Supplier shall monitor against each Performance Indicator and report the level actually achieved "
                       "to the Authority in the Performance Monitoring Report.")
        _table(doc, ["KPI", "Indicator", "Target Performance Level", "Measure", "Reporting"], kpis)

    out = io.BytesIO()
    doc.save(out)
    return out.getvalue()
