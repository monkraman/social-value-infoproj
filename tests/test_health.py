import sys
import os
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "database" in data
    assert data["database"]["connected"] is True
    assert data["database"]["pgvector_installed"] is True
    assert data["database"]["pgvector_version"] is not None


def test_root_endpoint(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "docs_url" in response.json()
