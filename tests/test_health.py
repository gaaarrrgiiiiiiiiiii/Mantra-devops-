import pytest
from fastapi.testclient import TestClient


def test_health_check(client: TestClient):
    """Test liveness probe returns HTTP 200 and healthy status."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "mantra-backend"


def test_api_health_check(client: TestClient):
    """Test /api/health endpoint returns HTTP 200."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


def test_ready_check(client: TestClient):
    """Test readiness probe endpoint."""
    response = client.get("/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"
