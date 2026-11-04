# Backend

Production-oriented FastAPI backend for the first two Industrial Knowledge Intelligence features:

1. Universal Document Ingestion & Knowledge Graph Agent
2. Expert Knowledge Copilot

## Runtime Modes

- `IKI_REPOSITORY_BACKEND=memory`: tests and throwaway local runs.
- `IKI_REPOSITORY_BACKEND=sqlite`: durable local development using SQLAlchemy and SQLite.
- `IKI_REPOSITORY_BACKEND=postgres`: PostgreSQL, pgvector and full-text retrieval, with Alembic migrations before startup. Automatic schema creation defaults to false for this backend.
- `IKI_STORAGE_BACKEND=local`: stores raw uploaded documents under `IKI_LOCAL_STORAGE_PATH`.
- `IKI_STORAGE_BACKEND=s3`: stores raw uploaded documents in private S3-compatible object storage.
- `IKI_REQUIRE_API_KEY=true`: protects document, graph, and copilot endpoints with `IKI_API_KEY_HEADER`.
- `IKI_LLM_PROVIDER=deterministic`: offline cited-answer behavior for tests and cheap local demos.
- `IKI_LLM_PROVIDER=nvidia`: enables NVIDIA-hosted model calls for answer generation, reranking, and safety checks.
- `IKI_REDIS_URL=redis://...`: optional exact-cache L1. PostgreSQL semantic cache remains source of truth.

## Local Run

```bash
python3 -m pip install -r requirements.txt
uvicorn backend.app.main:app --reload
```

The backend reads `backend/.env`. Use that file for local secrets such as `NVIDIA_API_KEY`; it is ignored by Git and Docker build context.

Optional ML-backed retrieval/NLP:

```bash
python3 -m pip install -r requirements-ml.txt
IKI_EMBEDDING_BACKEND=sentence-transformers
IKI_EMBEDDING_MODEL=BAAI/bge-base-en-v1.5
IKI_EMBEDDING_DIMENSION=768
```

Optional NVIDIA-backed copilot generation:

```bash
IKI_LLM_PROVIDER=nvidia
NVIDIA_API_KEY=replace-with-nvidia-key
IKI_NVIDIA_BASE_URL=https://integrate.api.nvidia.com/v1
IKI_DEFAULT_ANSWER_MODEL=qwen/qwen3-next-80b-a3b-instruct
IKI_ESCALATION_MODEL=deepseek-ai/deepseek-v4-pro
IKI_LONG_CONTEXT_MODEL=z-ai/glm-5.2
```

## Production Database

Run `alembic -c backend/alembic.ini upgrade head` from the repository, or
`alembic upgrade head` inside the backend image, before PostgreSQL startup.
The URL comes from `IKI_DATABASE_URL`; no credential is written to alembic.ini.
Revision `0001_legacy_baseline` creates a frozen schema or adopts compatible
existing tables. Revision `0002_native_retrieval` enables pgvector, adds
768-dimensional vectors and generated search text, backfills saved JSON vectors,
and creates GIN/full-text and HNSW/cosine indexes. Existing documents and JSON
vectors are retained. Malformed or incompatible vectors abort the transaction
instead of silently dropping or truncating data. The application rejects an
unmigrated PostgreSQL database or an incompatible embedding dimension.

The migration role needs schema/DDL and extension permissions. Run migrations
as a controlled deployment step; the API does not run startup DDL. SQLite local
development still defaults to automatic ORM table creation.

For production, set:

```bash
IKI_REPOSITORY_BACKEND=postgres
IKI_DATABASE_URL=postgresql+asyncpg://user:password@host:5432/industrial_intel
IKI_STORAGE_BACKEND=s3
IKI_S3_BUCKET=private-industrial-documents
IKI_AUTO_CREATE_SCHEMA=false
IKI_REQUIRE_API_KEY=true
IKI_API_KEY=replace-with-secret
IKI_LLM_PROVIDER=nvidia
NVIDIA_API_KEY=replace-with-nvidia-key
IKI_REDIS_URL=redis://redis:6379/0
```

Then run migrations before launching the app:

```bash
python3 -m alembic upgrade head
```

The single-host deployment takes a verified S3 database backup before migration.
Migrations are additive and forward-only: roll back to the previous compatible
application image rather than deleting columns/tables. Protected previous runtime
configuration is saved at `/root/mantra-previous-release.env` only after migration
succeeds; restore a verified backup into a separate database if data recovery is
needed. Review/repair incompatible legacy data before retrying a failed upgrade.
Changing embedding dimensions/models requires an explicit new migration and data
reindexing. Lock waits are bounded to 15 seconds and each migration statement to
five minutes; larger datasets need a separately planned backfill/index rollout.

Run the real PostgreSQL tests with `MANTRA_TEST_POSTGRES_URL` pointing to a
disposable server with CREATE DATABASE rights. Tests create random databases and
verify empty/populated upgrades, backfills, repeated upgrade, transaction rollback,
native retrieval, semantic cache and restart persistence. Never point test setup
at production credentials.

## Current Honesty Note

The API has durable SQLAlchemy persistence, raw document storage, generated chunk embeddings, database-native PostgreSQL hybrid retrieval, optional API-key protection, request audit persistence, LangGraph copilot orchestration, PostgreSQL semantic cache, optional Redis exact cache, and live-tested NVIDIA model provider calls for rerank and answer generation. Local/test retrieval uses deterministic hashing embeddings when sentence-transformers is unavailable. Domain benchmark evaluation is still needed before claiming plant-level answer quality.
