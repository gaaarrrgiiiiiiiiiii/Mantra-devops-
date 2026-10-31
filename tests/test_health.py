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
    assert data == {"status": "ready", "database": "connected", "redis": "disabled"}


@pytest.mark.parametrize("path", ["/ready", "/api/ready"])
def test_readiness_checks_database(client, monkeypatch, path):
    from unittest.mock import AsyncMock

    check = AsyncMock(side_effect=ConnectionError("database offline"))
    monkeypatch.setattr(client.app.state.repository, "count_documents", check)
    response = client.get(path)
    assert response.status_code == 503
    assert response.json() == {"status": "not_ready", "database": "unavailable", "redis": "disabled"}
    check.assert_awaited_once()


@pytest.mark.parametrize("available", [True, False])
def test_readiness_checks_configured_redis(client, monkeypatch, available):
    from types import SimpleNamespace
    from unittest.mock import AsyncMock

    settings = client.app.state.ingestion.settings
    monkeypatch.setattr(settings, "redis_url", "redis://test-only:6379")
    ping = AsyncMock(return_value=True) if available else AsyncMock(side_effect=ConnectionError("cache offline"))
    monkeypatch.setattr(client.app.state.copilot, "exact_cache", SimpleNamespace(client=SimpleNamespace(ping=ping)))
    response = client.get("/ready")
    assert response.status_code == (200 if available else 503)
    assert response.json()["database"] == "connected"
    assert response.json()["redis"] == ("connected" if available else "unavailable")
    ping.assert_awaited_once()


def test_liveness_survives_database_failure(client, monkeypatch):
    from unittest.mock import AsyncMock

    check = AsyncMock(side_effect=ConnectionError("database offline"))
    monkeypatch.setattr(client.app.state.repository, "count_documents", check)
    assert client.get("/health").status_code == 200
    check.assert_not_awaited()


def test_prometheus_metrics(client):
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "text/plain" in response.headers["content-type"]
    assert "http_requests_total" in response.text


@pytest.mark.parametrize("path", ["/health", "/api/health", "/ready", "/api/ready", "/metrics"])
def test_monitoring_bypasses_database_audit_and_rate_limits(client, monkeypatch, path):
    from unittest.mock import AsyncMock

    audit = AsyncMock(side_effect=ConnectionError("audit database offline"))
    monkeypatch.setattr(client.app.state.repository, "add_audit_event", audit)
    monkeypatch.setattr(client.app.state.ingestion.settings, "rate_limit_per_minute", 1)
    for _ in range(3):
        assert client.get(path).status_code == 200
    audit.assert_not_awaited()
