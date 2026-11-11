import os
import sys
import uuid

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import app
from app.core.database import SessionLocal
from app.core.security import generate_strong_password, hash_password
from app.models.user import User

# Throwaway accounts created for this test run only. They get a random password and are
# deleted afterwards, so no credential ever lives in the repo or stays in the database.
TEST_EMAIL_PREFIX = "pytest-"
TEST_EMAIL_DOMAIN = "@pytest.example.com"


def make_test_user(role: str = "superadmin") -> tuple[str, str]:
    email = f"{TEST_EMAIL_PREFIX}{role}-{uuid.uuid4().hex[:8]}{TEST_EMAIL_DOMAIN}"
    password = generate_strong_password()
    with SessionLocal() as db:
        db.add(User(name=f"Pytest {role}", email=email, password_hash=hash_password(password),
                    role=role, is_active=True))
        db.commit()
    return email, password


def login_headers(email: str, password: str) -> dict:
    with TestClient(app) as anon:
        res = anon.post("/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200, res.text
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


@pytest.fixture(scope="session", autouse=True)
def _cleanup_test_users():
    yield
    with SessionLocal() as db:
        db.query(User).filter(User.email.like(f"{TEST_EMAIL_PREFIX}%{TEST_EMAIL_DOMAIN}")).delete(
            synchronize_session=False
        )
        db.commit()


@pytest.fixture(scope="session")
def admin_credentials():
    return make_test_user("superadmin")


@pytest.fixture(scope="session")
def auth_headers(admin_credentials):
    """Bearer header for a throwaway superadmin, for calling protected endpoints."""
    return login_headers(*admin_credentials)


@pytest.fixture
def authed_client(auth_headers):
    """TestClient that sends the superadmin token on every request."""
    return TestClient(app, headers=auth_headers)
