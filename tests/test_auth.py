import uuid

from fastapi.testclient import TestClient

from app.main import app
from app.core.security import (
    create_access_token,
    generate_strong_password,
    hash_password,
    password_policy_errors,
    verify_password,
    needs_rehash,
)
from tests.conftest import TEST_EMAIL_DOMAIN, TEST_EMAIL_PREFIX, login_headers, make_test_user

client = TestClient(app)


def _new_email(tag: str) -> str:
    return f"{TEST_EMAIL_PREFIX}{tag}-{uuid.uuid4().hex[:8]}{TEST_EMAIL_DOMAIN}"


def test_auth_status_reveals_no_accounts():
    data = client.get("/auth/status").json()
    assert data["auth_enabled"] is True
    assert "default_superadmin_email" not in data
    assert "default_superadmin_available" not in data


def test_demo_account_cannot_sign_in():
    res = client.post("/auth/login", json={"email": "admin@infosys.com", "password": "admin123"})
    assert res.status_code == 401


def test_login_and_profile(admin_credentials):
    email, password = admin_credentials
    res = client.post("/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200
    token = res.json()["access_token"]
    profile = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"}).json()
    assert profile["email"] == email
    assert profile["role"] == "superadmin"


def test_login_invalid_password(admin_credentials):
    res = client.post("/auth/login", json={"email": admin_credentials[0], "password": "Wrong-Password-99"})
    assert res.status_code == 401


def test_unauthorized_profile_access():
    assert client.get("/auth/me").status_code == 401


def test_forged_token_rejected():
    # A token signed with the old hard-coded key must not work.
    import base64, hashlib, hmac, json
    def b64(b): return base64.urlsafe_b64encode(b).decode().rstrip("=")
    head = b64(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    body = b64(json.dumps({"sub": str(uuid.uuid4()), "role": "superadmin", "exp": 9999999999}).encode())
    sig = b64(hmac.new(b"infosys-social-value-rfp-builder-secure-enterprise-jwt-key",
                       f"{head}.{body}".encode(), hashlib.sha256).digest())
    assert client.get("/auth/me", headers={"Authorization": f"Bearer {head}.{body}.{sig}"}).status_code == 401


def test_alg_none_token_rejected():
    token = create_access_token({"sub": str(uuid.uuid4())})
    head, body, _ = token.split(".")
    import base64, json
    none_head = base64.urlsafe_b64encode(json.dumps({"alg": "none"}).encode()).decode().rstrip("=")
    assert client.get("/auth/me", headers={"Authorization": f"Bearer {none_head}.{body}."}).status_code == 401


def test_public_register_is_closed():
    res = client.post("/auth/register", json={
        "name": "Outsider", "email": _new_email("outsider"),
        "password": generate_strong_password(), "role": "superadmin",
    })
    assert res.status_code == 401


def test_non_admin_cannot_register_users():
    headers = login_headers(*make_test_user("bid_author"))
    res = client.post("/auth/register", headers=headers, json={
        "name": "Someone New", "email": _new_email("blocked"), "password": generate_strong_password(),
    })
    assert res.status_code == 403


def test_admin_registers_user_with_least_privilege(auth_headers):
    email, password = _new_email("author"), generate_strong_password()
    res = client.post("/auth/register", headers=auth_headers, json={
        "name": "Bid Author", "email": email, "password": password,
    })
    assert res.status_code == 201, res.text
    assert res.json()["role"] == "bid_author"
    assert client.post("/auth/login", json={"email": email, "password": password}).status_code == 200


def test_weak_password_rejected(auth_headers):
    for weak in ["admin123", "SecurePassword", "password1234!A", "Short1!a"]:
        res = client.post("/auth/register", headers=auth_headers, json={
            "name": "Weak Pw", "email": _new_email("weak"), "password": weak,
        })
        assert res.status_code == 422, weak


def test_unknown_role_rejected(auth_headers):
    res = client.post("/auth/register", headers=auth_headers, json={
        "name": "Role Test", "email": _new_email("role"), "password": generate_strong_password(), "role": "god",
    })
    assert res.status_code == 422


def test_lockout_after_repeated_failures():
    email, password = make_test_user("reviewer")
    for _ in range(5):
        assert client.post("/auth/login", json={"email": email, "password": "Not-The-Password-1"}).status_code == 401
    res = client.post("/auth/login", json={"email": email, "password": password})
    assert res.status_code == 429
    assert "Retry-After" in res.headers


def test_change_password():
    email, password = make_test_user("bid_author")
    headers = login_headers(email, password)
    new_pw = generate_strong_password()
    assert client.post("/auth/change-password", headers=headers,
                       json={"current_password": "Wrong-Current-1!", "new_password": new_pw}).status_code == 400
    assert client.post("/auth/change-password", headers=headers,
                       json={"current_password": password, "new_password": "weakpass12345"}).status_code == 400
    assert client.post("/auth/change-password", headers=headers,
                       json={"current_password": password, "new_password": new_pw}).status_code == 204
    assert client.post("/auth/login", json={"email": email, "password": new_pw}).status_code == 200


def test_password_policy_and_hash_upgrade():
    assert password_policy_errors(generate_strong_password()) == []
    assert "not your name or email" in password_policy_errors("Janedoe#2026xx", email="janedoe@x.com")
    import hashlib, secrets
    salt = secrets.token_hex(16)
    legacy = f"{salt}${hashlib.pbkdf2_hmac('sha256', b'Legacy-Pass-123', salt.encode(), 100_000).hex()}"
    assert verify_password("Legacy-Pass-123", legacy) and needs_rehash(legacy)
    assert not needs_rehash(hash_password("Fresh-Pass-1234"))
