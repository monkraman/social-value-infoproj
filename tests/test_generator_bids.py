"""Bids written in the RFP editor: shared with the team, changed only by their author, exported to Word."""
import io

import pytest
from docx import Document as WordDocument
from fastapi.testclient import TestClient

from app.api.generator_bids import render_docx
from app.main import app
from tests.conftest import login_headers, make_test_user

anon = TestClient(app)

DOC = {
    "title": "Test bid",
    "client": "Test Trust",
    "blocks": [{
        "ref": "SV2", "mac": "MAC 2.2", "heading": "Employment",
        "sections": [{"heading": "Summary", "paragraphs": ["Infosys will recruit locally."], "bullets": ["Cohort one"],
                      "table": {"head": ["When", "Step"], "rows": [["Month 1", "Recruit"]]}}],
        "kpis": [{"ref": "SV-KPI1", "indicator": "Weeks of apprenticeship", "target": "480", "measure": "NT10", "cycle": "Quarterly"}],
    }],
}
BID = {"title": "Test bid", "client": "Test Trust", "framework": "PPN0620", "initiative_count": 1, "document": DOC}


def test_word_layout_follows_schedule_8():
    text = "\n".join(p.text for p in WordDocument(io.BytesIO(render_docx(DOC))).paragraphs)
    assert "ANNEX 6 – SOCIAL VALUE" in text and "SECTION A – DELIVERABLES" in text
    assert "SV2 / (MAC 2.2)  EMPLOYMENT" in text
    assert "1.2\tInfosys will recruit locally." in text and "(a)\tCohort one" in text
    assert "SCHEDULE 3b" in text


def test_bids_require_login():
    assert anon.get("/generator/bids").status_code == 401
    assert anon.post("/generator/bids/docx", json={"document": DOC}).status_code == 401


def test_save_share_and_only_author_changes(authed_client):
    created = authed_client.post("/generator/bids", json=BID)
    assert created.status_code == 201, created.text
    bid_id = created.json()["id"]
    other = TestClient(app, headers=login_headers(*make_test_user("bid_author")))
    assert any(b["id"] == bid_id and not b["mine"] for b in other.get("/generator/bids").json())
    assert other.get(f"/generator/bids/{bid_id}").json()["document"]["title"] == "Test bid"
    assert other.put(f"/generator/bids/{bid_id}", json=BID).status_code == 403
    assert other.delete(f"/generator/bids/{bid_id}").status_code == 403
    assert authed_client.put(f"/generator/bids/{bid_id}", json={**BID, "status": "Submitted"}).json()["status"] == "Submitted"
    word = authed_client.post("/generator/bids/docx", json={"document": DOC})
    assert word.status_code == 200 and word.content[:2] == b"PK"
    assert authed_client.delete(f"/generator/bids/{bid_id}").status_code == 204
