"""Initiative Generator API: auth, form validation, and the AI -> code valuation hand-off (AI mocked)."""
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services import generator_service
from app.services.llm_client import LLMUnavailable

anon = TestClient(app)
BODY = {"company": "Infosys", "bid_amount_gbp": 10_000_000, "sv_percent": 10, "region": "North East", "duration_years": 3, "themes": ["Work"]}

AI_OUTPUT = {
    "initiatives": [
        {
            "name": "School code clubs",
            "theme": "Work",
            "attribution": "Infosys",
            "lines": [{"measure": "NT8", "units": 600, "basis": "200 hrs x 3 yrs", "value": 99999}],
            "bid_paragraph": "Infosys staff will run weekly code clubs.",
            "questions": ["Which schools?"],
        }
    ]
}


def test_generator_requires_login():
    assert anon.get("/generator/options").status_code == 401
    assert anon.post("/generator/run", json=BODY).status_code == 401


def test_options_come_from_tables(authed_client):
    data = authed_client.get("/generator/options").json()
    assert "North East" in data["regions"] and "Work" in data["themes"]
    assert data["tables"]["edition"]


def test_unknown_region_rejected(authed_client):
    assert authed_client.post("/generator/run", json={**BODY, "region": "Atlantis"}).status_code == 422


def test_run_values_ai_output_in_code(authed_client, monkeypatch):
    captured = {}

    def fake(system, user):
        captured["system"], captured["user"] = system, user
        return AI_OUTPUT

    monkeypatch.setattr(generator_service, "complete_json", fake)
    data = authed_client.post("/generator/run", json=BODY).json()

    assert "No values from you" in captured["system"]  # rules are in the prompt
    assert '"target_value_gbp": 1000000.0' in captured["user"]  # target sizes the units
    ini = data["initiatives"][0]
    assert ini["value_gbp"] == pytest.approx(600 * 17.48)  # AI's 99999 ignored
    assert ini["cost_gbp"] is None
    assert data["target_gbp"] == 1_000_000


def test_ai_unavailable_returns_503(authed_client, monkeypatch):
    def down(system, user):
        raise LLMUnavailable("Gemini returned HTTP 429")

    monkeypatch.setattr(generator_service, "complete_json", down)
    res = authed_client.post("/generator/run", json=BODY)
    assert res.status_code == 503 and "429" in res.json()["detail"]


def test_parse_requires_login_and_fills_form(authed_client):
    assert anon.post("/generator/parse", json={"text": "£10M"}).status_code == 401
    data = authed_client.post("/generator/parse", json={"text": "£10M, 3 years, 10% SV, Birmingham City Council, youth jobs"}).json()
    assert data["form"]["region"] == "West Midlands"
    assert data["missing"] == []


def test_brief_and_client_reach_the_ai_but_not_the_numbers(authed_client, monkeypatch):
    captured = {}

    def fake(system, user):
        captured["user"] = user
        return AI_OUTPUT

    monkeypatch.setattr(generator_service, "complete_json", fake)
    body = {**BODY, "client": "Birmingham City Council", "brief": "Focus on digital inclusion. Budget £99M."}
    data = authed_client.post("/generator/run", json=body).json()
    assert "digital inclusion" in captured["user"] and "Birmingham City Council" in captured["user"]
    assert data["target_gbp"] == 1_000_000  # from the form, not the £99M in the brief
