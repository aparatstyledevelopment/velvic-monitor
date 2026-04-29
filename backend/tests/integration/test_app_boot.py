"""Smoke test: the FastAPI app boots and exposes the OpenAPI schema."""

from fastapi.testclient import TestClient

from app.main import create_app


def test_openapi_served() -> None:
    client = TestClient(create_app())
    resp = client.get("/api/openapi.json")
    assert resp.status_code == 200
    spec = resp.json()
    assert spec["info"]["title"] == "Velvic Monitor API"


def test_auth_routes_registered() -> None:
    client = TestClient(create_app())
    spec = client.get("/api/openapi.json").json()
    paths = spec.get("paths", {})
    assert "/api/auth/signup" in paths
    assert "/api/auth/login" in paths
    assert "/api/auth/logout" in paths
    assert "/api/auth/me" in paths
    assert "/api/health" in paths
