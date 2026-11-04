import os

from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from .db_models import Base

SCHEMA_REVISION = '0002_native_retrieval'


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
    if engine.dialect.name == 'postgresql':
        raise RuntimeError('Run alembic upgrade head before PostgreSQL startup; set IKI_AUTO_CREATE_SCHEMA=false.')
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)


async def verify_postgres_schema(engine: AsyncEngine) -> None:
    """Fail startup if migration delivery was skipped or targets another release."""
    async with engine.connect() as connection:
        present = await connection.scalar(text("SELECT to_regclass('public.alembic_version') IS NOT NULL"))
        if not present:
            raise RuntimeError('PostgreSQL has no migration history. Run alembic upgrade head before startup.')
        versions = (await connection.execute(text('SELECT version_num FROM alembic_version'))).scalars().all()
        if versions != [SCHEMA_REVISION]:
            raise RuntimeError('PostgreSQL migration revision does not match this application release.')
