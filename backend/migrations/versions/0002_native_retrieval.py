"""Backfill 768-dimensional native retrieval and semantic-cache vectors."""
from alembic import op
from sqlalchemy import text

revision = '0002_native_retrieval'
down_revision = '0001_legacy_baseline'
branch_labels = None
depends_on = None


def upgrade():
    connection = op.get_bind()
    if connection.dialect.name != 'postgresql':
        return
    op.execute('CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA public')
    op.execute('ALTER TABLE document_chunks ADD COLUMN IF NOT EXISTS embedding vector(768)')
    op.execute('ALTER TABLE document_chunks ALTER COLUMN embedding TYPE vector(768) USING embedding::vector(768)')
    op.execute("ALTER TABLE document_chunks ADD COLUMN IF NOT EXISTS ts_content tsvector GENERATED ALWAYS AS (to_tsvector('english', content)) STORED")
    generated = connection.execute(text("SELECT is_generated FROM information_schema.columns WHERE table_schema='public' AND table_name='document_chunks' AND column_name='ts_content'")).scalar_one()
    if generated != 'ALWAYS':
        raise RuntimeError('Existing ts_content must be a generated search column; reconcile before retrying.')
    op.execute('ALTER TABLE semantic_query_cache ADD COLUMN IF NOT EXISTS query_embedding vector(768)')
    op.execute('ALTER TABLE semantic_query_cache ALTER COLUMN query_embedding TYPE vector(768) USING query_embedding::vector(768)')
    # Invalid JSON/non-finite/wrong-size vectors abort the transaction. Never truncate,
    # replace model embeddings or silently stamp an incomplete backfill as successful.
    op.execute("UPDATE document_chunks SET embedding=CAST(embedding_json AS vector(768)) WHERE embedding IS NULL AND embedding_json IS NOT NULL AND embedding_json::jsonb <> '[]'::jsonb")
    op.execute("UPDATE semantic_query_cache SET query_embedding=CAST(query_embedding_json AS vector(768)) WHERE query_embedding IS NULL AND query_embedding_json IS NOT NULL AND query_embedding_json::jsonb <> '[]'::jsonb")
    op.execute('CREATE INDEX IF NOT EXISTS ix_document_chunks_ts_content_gin ON document_chunks USING gin(ts_content)')
    op.execute('CREATE INDEX IF NOT EXISTS ix_document_chunks_embedding_hnsw ON document_chunks USING hnsw(embedding vector_cosine_ops)')
    op.execute('CREATE INDEX IF NOT EXISTS ix_semantic_cache_embedding_hnsw ON semantic_query_cache USING hnsw(query_embedding vector_cosine_ops)')


def downgrade():
    raise RuntimeError('Retrieval migration is additive and forward-only; the previous application image can use the retained JSON columns.')
