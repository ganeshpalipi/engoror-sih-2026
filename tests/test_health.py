"""
Phase 1 smoke tests: the app boots, /health works, the database connects.

Run from the RootVerse root folder:
    python -m pytest tests -v
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture()
def client():
    # Context-manager form triggers the lifespan (startup) event,
    # exactly like a real uvicorn process does.
    with TestClient(app) as test_client:
        yield test_client


def test_health_returns_ok(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["app"] == "RootVerse"
    assert data["offline_mode"] is True
    assert data["components"]["api"]["status"] == "ok"
    assert data["components"]["database"]["status"] == "ok"


def test_root_returns_service_info(client):
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["app"] == "RootVerse"
    assert data["docs_url"] == "/docs"
    assert data["health_url"] == "/health"


def test_unknown_route_returns_404(client):
    response = client.get("/api/does-not-exist")
    assert response.status_code == 404
