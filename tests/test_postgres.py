"""Opt-in test: MANTRA_TEST_POSTGRES_URL needs CREATE DATABASE/EXTENSION rights.

Creates and drops its own randomly named database; existing tables are untouched.
"""
import os
from uuid import uuid4

import httpx
import pytest
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import create_async_engine

from app.config import Settings
from app.main import create_app


@pytest.mark.skipif(not os.getenv("MANTRA_TEST_POSTGRES_URL"), reason="Set MANTRA_TEST_POSTGRES_URL to run against pgvector PostgreSQL")
@pytest.mark.asyncio
async def test_fresh_postgres_upload_and_copilot(tmp_path):
    url = make_url(os.environ["MANTRA_TEST_POSTGRES_URL"])
    database_name = f"mantra_test_{uuid4().hex}"
    admin = create_async_engine(url, isolation_level="AUTOCOMMIT")
    try:
        async with admin.connect() as connection:
            await connection.execute(text(f'CREATE DATABASE "{database_name}"'))
            try:
                settings = Settings(
                    _env_file=None, environment="test", repository_backend="postgres",
                    database_url=url.set(database=database_name).render_as_string(hide_password=False),
                    storage_backend="local", local_storage_path=str(tmp_path / "storage"),
                    embedding_backend="hashing", llm_provider="deterministic", redis_url="",
                    require_api_key=True, api_key="test-only-key", rate_limit_per_minute=0,
                )
                app = create_app(settings)
                async with app.router.lifespan_context(app):
                    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test", headers={"X-API-Key": settings.api_key}) as client:
                        payload = b"Pump P-205B bearing failure caused vibration. Replace the bearing."
                        uploaded = await client.post("/api/documents/upload", files={"file": ("test.txt", payload, "text/plain")})
                        assert uploaded.status_code == 200, uploaded.text
                        document_id = uploaded.json()["id"]
                        for _ in range(2):
                            answer = await client.post("/api/copilot/ask", json={"question": "P-205B bearing failure"})
                            assert answer.status_code == 200, answer.text
                            assert answer.json()["citations"][0]["document_id"] == document_id
                async with app.router.lifespan_context(app):
                    assert await app.state.repository.count_documents() == 1
            finally:
                await connection.execute(text(f'DROP DATABASE "{database_name}" WITH (FORCE)'))
    finally:
        await admin.dispose()
