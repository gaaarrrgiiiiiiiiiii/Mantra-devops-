import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

backend_path = Path(__file__).resolve().parent.parent / "backend"
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

from app.config import Settings
from app.main import create_app


@pytest.fixture
def client(tmp_path):
    # Isolate every test from developer .env files, production services, and stored data.
    settings = Settings(
        _env_file=None,
        environment="test",
        repository_backend="sqlite",
        database_url=f"sqlite+aiosqlite:///{tmp_path / 'test.db'}",
        storage_backend="local",
        local_storage_path=str(tmp_path / "storage"),
        embedding_backend="hashing",
        llm_provider="deterministic",
        redis_url="",
        require_api_key=True,
        api_key="test-only-key",
        rate_limit_per_minute=0,
        max_upload_bytes=1024,
    )
    with TestClient(create_app(settings), headers={"X-API-Key": settings.api_key}) as test_client:
        yield test_client
