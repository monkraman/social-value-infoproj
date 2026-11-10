import os
import sys

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import app

# Default superadmin seeded by the app (see test_auth.py).
TEST_ADMIN_EMAIL = "admin@infosys.com"
TEST_ADMIN_PASSWORD = "admin123"


@pytest.fixture(scope="session")
def auth_headers():
    """Bearer header for the default superadmin, for calling protected endpoints."""
    with TestClient(app) as anon:
        res = anon.post("/auth/login", json={"email": TEST_ADMIN_EMAIL, "password": TEST_ADMIN_PASSWORD})
    assert res.status_code == 200, res.text
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


@pytest.fixture
def authed_client(auth_headers):
    """TestClient that sends the superadmin token on every request."""
    return TestClient(app, headers=auth_headers)
