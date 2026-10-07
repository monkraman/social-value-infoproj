import sys
import os
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_list_documents(client):
    response = client.get("/documents")
    assert response.status_code == 200
    docs = response.json()
    assert isinstance(docs, list)
    assert len(docs) > 0
    filenames = [d["filename"] for d in docs]
    assert any("Birmingham" in fn for fn in filenames)


def test_search_endpoint(client):
    response = client.post(
        "/search",
        json={"query": "digital inclusion Birmingham", "top_k": 3}
    )
    assert response.status_code == 200
    data = response.json()
    assert "results" in data
    assert len(data["results"]) > 0
    top = data["results"][0]
    assert "chunk_id" in top
    assert "similarity" in top
    assert "content" in top
    assert "filename" in top


def test_response_generation_endpoint(client):
    response = client.post(
        "/responses/generate",
        json={
            "contract_duration_years": 3,
            "contract_value_gbp": 10000000,
            "social_value_weighting_percent": 10,
            "client": "Birmingham City Council",
            "location": "Birmingham",
            "priorities": ["Digital Inclusion", "Youth Employment"],
            "top_k": 4
        }
    )
    assert response.status_code == 200
    data = response.json()

    # Verify structured packages
    assert "core_package" in data
    assert "enhanced_package" in data
    assert "localised_package" in data
    assert "assumptions" in data
    assert "validation_required" in data

    # Verify deterministic calculation layer output
    core_calc = data["core_package"]["financial_calculation"]
    assert core_calc is not None
    assert "total_social_value_gbp" in core_calc
    assert "audit_trail" in core_calc
    assert len(core_calc["audit_trail"]) > 0

    enhanced_calc = data["enhanced_package"]["financial_calculation"]
    assert enhanced_calc is not None
    assert enhanced_calc["contract_value_gbp"] == 10000000.0
