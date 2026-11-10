"""Every non-auth API router must reject requests without a valid Bearer token."""
import pytest
from fastapi.testclient import TestClient

from app.main import app

anon = TestClient(app)

PROTECTED = [
    ("get", "/documents", None),
    ("delete", "/documents/00000000-0000-0000-0000-000000000000?permanent=true", None),
    ("post", "/search", {"query": "digital inclusion"}),
    ("get", "/responses/history", None),
    ("post", "/responses/prompt", {"prompt": "hello"}),
    ("get", "/calculations/metrics", None),
    ("get", "/calculations/partners", None),
    ("get", "/audit/summary", None),
]


@pytest.mark.parametrize("method,path,body", PROTECTED)
def test_protected_endpoint_requires_token(method, path, body):
    kwargs = {"json": body} if body is not None else {}
    assert getattr(anon, method)(path, **kwargs).status_code == 401


@pytest.mark.parametrize("method,path,body", PROTECTED[:1])
def test_protected_endpoint_rejects_bad_token(method, path, body):
    res = getattr(anon, method)(path, headers={"Authorization": "Bearer not-a-real-token"})
    assert res.status_code == 401


def test_protected_endpoint_accepts_valid_token(authed_client):
    assert authed_client.get("/calculations/metrics").status_code == 200


@pytest.mark.parametrize("path", ["/health", "/", "/auth/status"])
def test_public_endpoints_stay_open(path):
    assert anon.get(path).status_code == 200
