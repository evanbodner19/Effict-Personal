"""
Integration test — requires a running Supabase instance.
Set SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, SUPABASE_JWT_SECRET in .env.
Create a test user in Supabase Auth and generate a valid JWT.

These tests hit the real API endpoints with a real database.
Skip if env vars are not set.
"""
import os
import pytest
from fastapi.testclient import TestClient

# Skip entire module if no Supabase config
pytestmark = pytest.mark.skipif(
    not os.getenv("SUPABASE_URL") or "placeholder" in os.getenv("SUPABASE_URL", "placeholder"),
    reason="No real Supabase configured",
)


@pytest.fixture
def client():
    from backend.main import app
    return TestClient(app)


@pytest.fixture
def auth_headers():
    """Must set TEST_JWT in env — a valid Supabase JWT for a test user."""
    token = os.getenv("TEST_JWT", "")
    return {"Authorization": f"Bearer {token}"}


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_sync_all_requires_auth(client):
    resp = client.post("/api/sync/all")
    assert resp.status_code in (401, 422)


def test_top_requires_auth(client):
    resp = client.get("/api/top")
    assert resp.status_code in (401, 422)


def test_full_flow(client, auth_headers):
    """Smoke test: sync -> get top -> create item -> complete -> verify."""
    # Sync (seeds data on first run)
    resp = client.post("/api/sync/all?lat=33.31&lng=-111.84&tz=America/Phoenix", headers=auth_headers)
    assert resp.status_code == 200

    # Get categories (should have seed data)
    resp = client.get("/api/categories", headers=auth_headers)
    assert resp.status_code == 200
    categories = resp.json()
    assert len(categories) >= 6

    # Get top
    resp = client.get("/api/top", headers=auth_headers)
    assert resp.status_code == 200

    # Create item
    cat_id = categories[0]["id"]
    resp = client.post(
        "/api/items",
        headers=auth_headers,
        json={"title": "Test Item", "category_id": cat_id},
    )
    assert resp.status_code == 200
    item_id = resp.json()["id"]

    # Complete item
    resp = client.post(f"/api/items/{item_id}/complete", headers=auth_headers)
    assert resp.status_code == 200
