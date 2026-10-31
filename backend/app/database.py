import os

from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from .db_models import Base


def create_engine_and_session_factory(database_url: str) -> tuple[AsyncEngine, async_sessionmaker[AsyncSession]]:
    connect_args = {}
    if database_url.startswith("sqlite"):
        db_path = make_url(database_url).database
        if db_path and db_path != ":memory:":
            os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
        connect_args = {"check_same_thread": False}

    engine = create_async_engine(database_url, echo=False, future=True, connect_args=connect_args)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    return engine, session_factory


async def initialize_database(engine: AsyncEngine) -> None:
    async with engine.begin() as connection:
        if engine.dialect.name == "postgresql":
            await connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA public"))
        await connection.run_sync(Base.metadata.create_all)
        if engine.dialect.name == "postgresql":
            # create_all cannot create the PostgreSQL-only columns used by hybrid retrieval.
            await connection.execute(text("ALTER TABLE document_chunks ADD COLUMN IF NOT EXISTS embedding vector"))
            await connection.execute(text(
                "ALTER TABLE document_chunks ADD COLUMN IF NOT EXISTS ts_content tsvector "
                "GENERATED ALWAYS AS (to_tsvector('english', content)) STORED"
            ))
            await connection.execute(text("ALTER TABLE semantic_query_cache ADD COLUMN IF NOT EXISTS query_embedding vector"))
