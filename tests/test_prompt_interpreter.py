import sys
import os
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_natural_language_prompt_rfp(client):
    """Verifies that a full natural language prompt reaches backend and generates packages."""
    prompt_text = (
        "I need to build a Social Value bid response, for a 3-year contract of £10M with 10% "
        "Social Value weighting. The client Birmingham City Council in Birmingham wants the Social "
        "Value offer to address digital inclusion and youth employment."
    )
    response = client.post("/responses/prompt", json={"prompt": prompt_text})
    assert response.status_code == 200
    data = response.json()
    assert data["is_rfp_prompt"] is True
    assert data["intent"] == "rfp_opportunity"
    assert data["prompt_id"] is not None
    assert data["result"] is not None
    assert "localised_package" in data["result"]
    assert data["result"]["localised_package"]["financial_calculation"]["target_met"] is True


def test_natural_language_prompt_non_rfp(client):
    """Verifies that random/irrelevant prompts ('harkuch prompt') are safely identified by the backend."""
    prompt_text = "What is the capital of France and tell me a funny story?"
    response = client.post("/responses/prompt", json={"prompt": prompt_text})
    assert response.status_code == 200
    data = response.json()
    assert data["is_rfp_prompt"] is False
    assert data["intent"] == "non_rfp"
    assert "not contain recognized tender" in data["explanation"]
    assert data["result"] is None


def test_natural_language_prompt_generic_without_birmingham(client):
    """Verifies that a prompt without client/location does NOT default to Birmingham."""
    prompt_text = (
        "I need to build a Social Value bid response, for a 3-year contract of £10M with 10% "
        "Social Value weighting."
    )
    response = client.post("/responses/prompt", json={"prompt": prompt_text})
    assert response.status_code == 200
    data = response.json()
    assert data["is_rfp_prompt"] is True
    assert data["request"]["client"] != "Birmingham City Council"
    assert data["request"]["location"] != "Birmingham"
    assert "Birmingham" not in data["request"]["client"]
    assert "Birmingham" not in data["request"]["location"]
    assert data["request"]["client"] == "UK Public Sector Authority"
    assert data["request"]["location"] == "UK Regional"


def test_natural_language_prompt_custom_client(client):
    """Verifies that a custom client (e.g. Manchester) is correctly extracted instead of Birmingham."""
    prompt_text = (
        "I need to build a Social Value bid response, for a 4-year contract of £12M with 10% "
        "Social Value weighting. The client Manchester City Council in Manchester wants the Social "
        "Value offer to address local supply chain and green skills."
    )
    response = client.post("/responses/prompt", json={"prompt": prompt_text})
    assert response.status_code == 200
    data = response.json()
    assert data["is_rfp_prompt"] is True
    assert data["request"]["client"] == "Manchester City Council"
    assert data["request"]["location"] == "Manchester"
    assert "Local Supply Chain" in data["request"]["priorities"]
    assert "Net Zero & Environment" in data["request"]["priorities"]


def test_prompt_history_endpoint(client):
    """Verifies that past prompts are retrieved in audit history."""
    response = client.get("/responses/history")
    assert response.status_code == 200
    history = response.json()
    assert isinstance(history, list)
    assert len(history) >= 2
    # Verify the most recent prompt is recorded
    latest = history[0]
    assert "raw_prompt" in latest
    assert "intent" in latest
    assert "created_at" in latest
