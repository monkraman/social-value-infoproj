"""Saved Initiative Generator runs: each user sees and changes only their own."""
import pytest
from fastapi.testclient import TestClient

from app.main import app
from tests.conftest import login_headers, make_test_user

anon = TestClient(app)

RUN = {
    "title": "Test Council",
    "client": "Test Council",
    "region": "North East",
    "framework": "PPN002",
    "contract_value_gbp": 10_000_000,
    "target_gbp": 1_000_000,
    "value_gbp": 950_000,
    "initiative_count": 2,
    "state": {"version": 1, "initiatives": [{"id": "AI-1", "included": True}]},
}


@pytest.fixture(scope="module")
def other_client():
    """A second, unrelated user."""
    return TestClient(app, headers=login_headers(*make_test_user("bid_author")))


def test_runs_require_login():
    assert anon.get("/generator/runs").status_code == 401
    assert anon.post("/generator/runs", json=RUN).status_code == 401


def test_save_list_open_update_delete(authed_client):
    created = authed_client.post("/generator/runs", json=RUN)
    assert created.status_code == 201, created.text
    run_id = created.json()["id"]
    assert "state" not in created.json()

    listed = authed_client.get("/generator/runs").json()
    assert listed[0]["id"] == run_id and listed[0]["title"] == "Test Council"
    assert "state" not in listed[0]

    opened = authed_client.get(f"/generator/runs/{run_id}").json()
    assert opened["state"] == RUN["state"]

    changed = authed_client.put(f"/generator/runs/{run_id}", json={**RUN, "value_gbp": 1_200_000, "state": {"version": 1, "initiatives": []}})
    assert changed.status_code == 200 and changed.json()["value_gbp"] == 1_200_000
    assert authed_client.get(f"/generator/runs/{run_id}").json()["state"]["initiatives"] == []

    assert authed_client.delete(f"/generator/runs/{run_id}").status_code == 204
    assert authed_client.get(f"/generator/runs/{run_id}").status_code == 404


def test_runs_are_private(authed_client, other_client):
    run_id = authed_client.post("/generator/runs", json=RUN).json()["id"]
    try:
        assert run_id not in [r["id"] for r in other_client.get("/generator/runs").json()]
        assert other_client.get(f"/generator/runs/{run_id}").status_code == 404
        assert other_client.put(f"/generator/runs/{run_id}", json=RUN).status_code == 404
        assert other_client.delete(f"/generator/runs/{run_id}").status_code == 404
        assert authed_client.get(f"/generator/runs/{run_id}").status_code == 200
    finally:
        authed_client.delete(f"/generator/runs/{run_id}")


def test_bad_input_rejected(authed_client):
    assert authed_client.get("/generator/runs/not-a-uuid").status_code == 404
    assert authed_client.post("/generator/runs", json={**RUN, "title": ""}).status_code == 422
    huge = {"version": 1, "blob": "x" * 2_100_000}
    assert authed_client.post("/generator/runs", json={**RUN, "state": huge}).status_code == 422
