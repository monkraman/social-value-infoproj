"""Phase 1 gap fixes: initiative types (D3), evidence (P1), text extraction (P2), embeddings (L2)."""
import io

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app
from app.services.embedding_service import EmbeddingUnavailable, embedding_service
from app.services.generator_service import apply_initiative_types, build_prompt
from app.services.initiative_valuation import TenderForm
from app.knowledge import load_tables
from tests.conftest import login_headers, make_test_user


# ── D3: the Infosys-fit rating comes from the curated type, never from the AI ─────────────

def test_known_type_sets_curated_fit():
    result = {"initiatives": [{"name": "Laptops for residents"}], "checks": []}
    apply_initiative_types(result, {"initiatives": [{"type": "pat-09", "fit": "Core strength (AI says)"}]})
    t = result["initiatives"][0]["type"]
    assert t["id"] == "PAT-09" and t["fit"] == "Core strength"
    assert "Devices" in t["reason"]
    assert result["checks"] == []


def test_unknown_or_missing_type_is_unassessed():
    result = {"initiatives": [{"name": "A"}, {"name": "B"}], "checks": []}
    apply_initiative_types(result, {"initiatives": [{"type": "PAT-99"}, {}]})
    assert result["initiatives"][0]["type"] is None
    assert result["initiatives"][1]["type"] is None
    assert any("PAT-99" in c for c in result["checks"])


def test_prompt_lists_types_as_labels_only():
    form = TenderForm(company="Infosys", bid_amount_gbp=10_000_000, sv_percent=10, region="North East", duration_years=3)
    system, user = build_prompt(form, load_tables())
    assert "INITIATIVE TYPES" in user and "not a menu" in user
    assert "Never change, add or drop an initiative" in system


# ── L2: no placeholder vectors unless explicitly allowed ──────────────────────────────────

def test_embedding_without_provider_raises(monkeypatch):
    monkeypatch.setattr(settings, "LLM_PROVIDER", "offline")
    monkeypatch.setattr(settings, "EMBEDDING_ALLOW_SYNTHETIC", False)
    with pytest.raises(EmbeddingUnavailable):
        embedding_service.get_embedding("digital inclusion")


def test_placeholder_vectors_only_when_allowed(monkeypatch):
    monkeypatch.setattr(settings, "LLM_PROVIDER", "offline")
    monkeypatch.setattr(settings, "EMBEDDING_ALLOW_SYNTHETIC", True)
    vec = embedding_service.get_embedding("digital inclusion")
    assert len(vec) == settings.EMBEDDING_DIMENSION


# ── P2: documents are read by the backend and not stored ─────────────────────────────────

@pytest.fixture(scope="module")
def author():
    email, password = make_test_user("bid_author")
    return login_headers(email, password)


def test_extract_requires_login():
    with TestClient(app) as anon:
        res = anon.post("/generator/extract", files={"file": ("a.txt", b"hello", "text/plain")})
    assert res.status_code in (401, 403)


def test_extract_reads_docx(author):
    docx = pytest.importorskip("docx")
    buf = io.BytesIO()
    d = docx.Document()
    d.add_paragraph("The council wants apprenticeships for care leavers.")
    d.save(buf)
    with TestClient(app) as client:
        res = client.post("/generator/extract", headers=author,
                          files={"file": ("policy.docx", buf.getvalue(),
                                          "application/vnd.openxmlformats-officedocument.wordprocessingml.document")})
    assert res.status_code == 200, res.text
    assert res.json() == {"name": "policy.docx", "text": "The council wants apprenticeships for care leavers."}


def test_extract_rejects_bad_input(author):
    with TestClient(app) as client:
        empty = client.post("/generator/extract", headers=author, files={"file": ("a.pdf", b"", "application/pdf")})
        wrong = client.post("/generator/extract", headers=author, files={"file": ("a.exe", b"MZ", "application/octet-stream")})
        broken = client.post("/generator/extract", headers=author, files={"file": ("a.pdf", b"not a pdf", "application/pdf")})
    assert empty.status_code == 400
    assert wrong.status_code == 422
    assert broken.status_code == 422


def test_document_text_unknown_id_is_404(author):
    with TestClient(app) as client:
        assert client.get("/generator/documents/not-a-uuid/text", headers=author).status_code == 404
        assert client.get("/generator/documents/00000000-0000-0000-0000-000000000000/text", headers=author).status_code == 404


# ── P1: evidence never breaks a run ───────────────────────────────────────────────────────

def test_evidence_search_down_leaves_a_note(monkeypatch):
    from app.api import generator as gen
    from app.core.database import SessionLocal

    def down(**_):
        raise EmbeddingUnavailable("test outage")

    monkeypatch.setattr(gen.retrieval_service, "search_chunks", down)
    result = {"initiatives": [{"name": "A", "description": "a"}], "checks": []}
    with SessionLocal() as db:
        gen.attach_evidence(result, db)
    assert result["initiatives"][0]["evidence"] == []
    # Either nothing is indexed, or search is down: both are said, never silently empty.
    assert any("evidence" in c.lower() for c in result["checks"])
