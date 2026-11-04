"""Real PostgreSQL acceptance; tests create/drop only their random databases."""
import asyncio
import json
import os
from pathlib import Path
from uuid import uuid4

from alembic import command
from alembic.config import Config
import httpx
import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import Settings
from app.database import SCHEMA_REVISION
from app.db_models import DocumentChunkRecord, DocumentRecord, SemanticCacheRecord
from app.main import create_app
from app.services.embeddings import HashingEmbeddingProvider
from migrations.legacy_schema import Base as LegacyBase

pytestmark = pytest.mark.skipif(not os.getenv('MANTRA_TEST_POSTGRES_URL'), reason='MANTRA_TEST_POSTGRES_URL required for disposable PostgreSQL tests')
PAYLOAD = 'Pump P-205B bearing failure caused vibration. Replace the bearing and inspect lubrication.'


async def upgrade(url, revision='head'):
    root = next(path for path in [Path(__file__).resolve().parents[1] / 'backend', Path.cwd()] if (path / 'alembic.ini').is_file())
    config = Config(str(root / 'alembic.ini'))
    config.attributes['database_url'] = url
    await asyncio.to_thread(command.upgrade, config, revision)


@pytest_asyncio.fixture
async def postgres_url():
    url = make_url(os.environ['MANTRA_TEST_POSTGRES_URL'])
    name = 'mantra_test_' + uuid4().hex
    admin = create_async_engine(url, isolation_level='AUTOCOMMIT')
    try:
        async with admin.connect() as connection:
            await connection.execute(text(f'CREATE DATABASE "{name}"'))
            try:
                yield url.set(database=name).render_as_string(hide_password=False)
            finally:
                await connection.execute(text(f'DROP DATABASE "{name}" WITH (FORCE)'))
    finally:
        await admin.dispose()


def settings_for(url, tmp_path):
    return Settings(_env_file=None, environment='test', repository_backend='postgres',
                    database_url=url, storage_backend='local', local_storage_path=str(tmp_path),
                    embedding_backend='hashing', llm_provider='deterministic', redis_url='',
                    require_api_key=True, api_key='test-only-key', rate_limit_per_minute=0,
                    auto_create_schema=False)


@pytest.mark.asyncio
async def test_fresh_postgres_migration_ingestion_native_retrieval_and_restart(postgres_url, tmp_path, monkeypatch):
    await upgrade(postgres_url)
    await upgrade(postgres_url)

    async def forbidden_fallback(*args, **kwargs):
        raise AssertionError('PostgreSQL must use native retrieval, not the Python fallback')

    monkeypatch.setattr('app.repository.application_level_search', forbidden_fallback)
    app = create_app(settings_for(postgres_url, tmp_path))
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://test', headers={'X-API-Key': 'test-only-key'}) as client:
            uploaded = await client.post('/api/documents/upload', files={'file': ('test.txt', PAYLOAD.encode(), 'text/plain')})
            assert uploaded.status_code == 200, uploaded.text
            document_id = uploaded.json()['id']
            for attempt in range(2):
                answer = await client.post('/api/copilot/ask', json={'question': 'P-205B bearing failure'})
                assert answer.status_code == 200, answer.text
                assert answer.json()['citations'][0]['document_id'] == document_id
                assert answer.json()['generation_status'] == 'deterministic'
                assert answer.json()['model_used'] is None
                assert answer.json()['cache_status'] == ('miss' if attempt == 0 else 'postgres_exact_hit')
            cached = await app.state.repository.find_semantic_cache(
                HashingEmbeddingProvider().embed('P-205B bearing failure'), 'deterministic',
                app.state.ingestion.settings.prompt_version, await app.state.repository.get_corpus_version(), 0.9,
            )
            assert cached is not None and cached.citations[0].document_id == document_id
            assert await app.state.repository.search_chunks('zzzznevermatch', ['zzzznevermatch'], [0.0] * 768, set(), 5) == []
        async with app.state.engine.connect() as connection:
            assert await connection.scalar(text('SELECT count(*) FROM document_chunks WHERE embedding IS NOT NULL AND ts_content IS NOT NULL')) > 0
            assert await connection.scalar(text('SELECT count(*) FROM semantic_query_cache WHERE query_embedding IS NOT NULL')) > 0
    async with app.router.lifespan_context(app):
        assert await app.state.repository.count_documents() == 1


@pytest.mark.asyncio
@pytest.mark.parametrize('startup_columns', [False, True])
async def test_unversioned_populated_upgrade_backfills_and_preserves_data(postgres_url, tmp_path, startup_columns):
    engine = create_async_engine(postgres_url)
    vector = HashingEmbeddingProvider().embed(PAYLOAD)
    try:
        async with engine.begin() as connection:
            await connection.run_sync(LegacyBase.metadata.create_all)
            if startup_columns:
                await connection.execute(text('CREATE EXTENSION IF NOT EXISTS vector'))
                await connection.execute(text('ALTER TABLE document_chunks ADD COLUMN embedding vector'))
                await connection.execute(text("ALTER TABLE document_chunks ADD COLUMN ts_content tsvector GENERATED ALWAYS AS (to_tsvector('english', content)) STORED"))
                await connection.execute(text('ALTER TABLE semantic_query_cache ADD COLUMN query_embedding vector'))
        async with async_sessionmaker(engine, expire_on_commit=False)() as session:
            session.add(DocumentRecord(id='legacy-document', filename='legacy.txt', content_type='text/plain', document_type='text', content_hash='legacy-hash', status='indexed'))
            await session.flush()
            session.add(DocumentChunkRecord(id='legacy-chunk', document_id='legacy-document', chunk_index=0, content=PAYLOAD, embedding_json=json.dumps(vector)))
            session.add(SemanticCacheRecord(normalized_query='bearing failure', query_embedding_json=json.dumps(vector), model_name='demo', prompt_version='v1', corpus_version=0, citation_hash='fixture', answer='Replace bearing', confidence='high', citations_json='[]', retrieved_chunk_count=1, query_type='technical'))
            await session.commit()
        await upgrade(postgres_url)
        await upgrade(postgres_url)
        async with engine.connect() as connection:
            assert await connection.scalar(text('SELECT version_num FROM alembic_version')) == SCHEMA_REVISION
            row = (await connection.execute(text("SELECT content,vector_dims(embedding),ts_content @@ to_tsquery('english','bearing') FROM document_chunks WHERE id='legacy-chunk'"))).one()
            assert row == (PAYLOAD, 768, True)
            assert await connection.scalar(text('SELECT vector_dims(query_embedding) FROM semantic_query_cache')) == 768
            assert await connection.scalar(text('SELECT count(*) FROM documents')) == 1
            indexes = set((await connection.execute(text("SELECT indexname FROM pg_indexes WHERE schemaname='public'"))).scalars())
            assert {'ix_document_chunks_ts_content_gin', 'ix_document_chunks_embedding_hnsw', 'ix_semantic_cache_embedding_hnsw'} <= indexes
        app = create_app(settings_for(postgres_url, tmp_path))
        async with app.router.lifespan_context(app):
            found = await app.state.repository.search_chunks('bearing failure', ['bearing', 'failure'], vector, set(), 5)
            assert found and found[0][1].id == 'legacy-document'
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_bad_vector_aborts_upgrade_without_losing_legacy_data(postgres_url):
    await upgrade(postgres_url, '0001_legacy_baseline')
    engine = create_async_engine(postgres_url)
    try:
        async with async_sessionmaker(engine)() as session:
            session.add(DocumentRecord(id='bad-dimension-doc', filename='legacy.txt', content_type='text/plain', document_type='text', content_hash='bad-hash', status='indexed'))
            await session.flush()
            session.add(DocumentChunkRecord(id='bad-vector', document_id='bad-dimension-doc', chunk_index=0, content=PAYLOAD, embedding_json='[1,2]'))
            await session.commit()
        with pytest.raises(Exception, match='dimensions'):
            await upgrade(postgres_url)
        async with engine.connect() as connection:
            assert await connection.scalar(text('SELECT version_num FROM alembic_version')) == '0001_legacy_baseline'
            assert await connection.scalar(text("SELECT embedding_json FROM document_chunks WHERE id='bad-vector'")) == '[1,2]'
            assert await connection.scalar(text('SELECT count(*) FROM documents')) == 1
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_postgres_startup_rejects_unmigrated_database(postgres_url, tmp_path):
    app = create_app(settings_for(postgres_url, tmp_path))
    with pytest.raises(RuntimeError, match='migration history'):
        async with app.router.lifespan_context(app):
            pass
