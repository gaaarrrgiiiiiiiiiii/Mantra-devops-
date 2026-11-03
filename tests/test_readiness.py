from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


def test_readiness_reports_unavailable_redis(tmp_path):
    settings = Settings(
        repository_backend="memory",
        local_storage_path=str(tmp_path),
        redis_url="redis://127.0.0.1:1/0",
        require_api_key=False,
    )
    with TestClient(create_app(settings)) as client:
        response = client.get("/ready")
        assert response.status_code == 503
        assert response.json()["redis"] == "unavailable"
        assert client.get("/health").status_code == 200


def test_readiness_reports_database_failure(tmp_path):
    class UnavailableDatabase:
        def connect(self):
            raise ConnectionError("database is offline")

    settings = Settings(
        repository_backend="memory",
        local_storage_path=str(tmp_path),
        redis_url="",
        require_api_key=False,
    )
    app = create_app(settings)
    with TestClient(app) as client:
        app.state.engine = UnavailableDatabase()
        response = client.get("/ready")
        assert response.status_code == 503
        assert response.json()["database"] == "unavailable"
        assert client.get("/health").status_code == 200
