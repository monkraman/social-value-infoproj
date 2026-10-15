import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_auth_status():
    response = client.get("/auth/status")
    assert response.status_code == 200
    data = response.json()
    assert data["auth_enabled"] is True
    assert data["default_superadmin_available"] is True
    assert data["default_superadmin_email"] == "admin@infosys.com"


def test_login_default_superadmin():
    response = client.post("/auth/login", json={
        "email": "admin@infosys.com",
        "password": "admin123"
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == "admin@infosys.com"
    assert data["user"]["role"] == "superadmin"


def test_login_invalid_password():
    response = client.post("/auth/login", json={
        "email": "admin@infosys.com",
        "password": "wrongpassword"
    })
    assert response.status_code == 401


def test_get_current_user_profile():
    # First login
    login_res = client.post("/auth/login", json={
        "email": "admin@infosys.com",
        "password": "admin123"
    })
    token = login_res.json()["access_token"]

    # Access /auth/me
    profile_res = client.get("/auth/me", headers={
        "Authorization": f"Bearer {token}"
    })
    assert profile_res.status_code == 200
    profile = profile_res.json()
    assert profile["email"] == "admin@infosys.com"
    assert profile["role"] == "superadmin"


def test_unauthorized_profile_access():
    response = client.get("/auth/me")
    assert response.status_code == 401


def test_register_and_login_new_user():
    import uuid
    unique_email = f"analyst_{uuid.uuid4().hex[:6]}@infosys.com"
    reg_res = client.post("/auth/register", json={
        "name": "Social Value Bid Author",
        "email": unique_email,
        "password": "SecurePassword123!",
        "role": "bid_author"
    })
    assert reg_res.status_code == 201
    reg_data = reg_res.json()
    assert reg_data["user"]["email"] == unique_email
    assert reg_data["user"]["role"] == "bid_author"
    assert "access_token" in reg_data

    # Login with the newly registered user
    login_res = client.post("/auth/login", json={
        "email": unique_email,
        "password": "SecurePassword123!"
    })
    assert login_res.status_code == 200
    assert login_res.json()["user"]["role"] == "bid_author"
