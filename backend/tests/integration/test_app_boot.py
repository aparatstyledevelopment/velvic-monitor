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


def test_briefing_routes_registered() -> None:
    client = TestClient(create_app())
    spec = client.get("/api/openapi.json").json()
    paths = spec.get("paths", {})
    assert "/api/companies/{company_id}/briefings/latest" in paths
    assert "/api/companies/{company_id}/briefings/{date}" in paths
    assert "/api/companies/{company_id}/briefings/{date}/evidence" in paths


def test_chat_routes_registered() -> None:
    client = TestClient(create_app())
    spec = client.get("/api/openapi.json").json()
    paths = spec.get("paths", {})
    assert "/api/chat/threads" in paths
    assert "/api/chat/threads/{thread_id}" in paths
    assert "/api/chat/threads/{thread_id}/turns" in paths


def test_phase3_routes_registered() -> None:
    client = TestClient(create_app())
    spec = client.get("/api/openapi.json").json()
    paths = spec.get("paths", {})
    assert "/api/me/companies" in paths
    assert "/api/engine_calls/{engine_call_id}" in paths


def test_phase3_drivers_routes_registered() -> None:
    client = TestClient(create_app())
    spec = client.get("/api/openapi.json").json()
    paths = spec.get("paths", {})
    assert "/api/companies/{company_id}/snapshot" in paths
    assert "/api/companies/{company_id}/drivers/data/{source}" in paths
