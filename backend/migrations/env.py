"""Run migrations with asyncpg without writing database credentials to configuration."""
import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool, text
from sqlalchemy.ext.asyncio import create_async_engine

from app.config import Settings
from app.db_models import Base

config = context.config
if config.config_file_name:
    fileConfig(config.config_file_name)


def migrate(connection):
    context.configure(connection=connection, target_metadata=Base.metadata, compare_type=True)
    with context.begin_transaction():
        if connection.dialect.name == 'postgresql':
            connection.execute(text("SET LOCAL lock_timeout = '15s'"))
            connection.execute(text("SET LOCAL statement_timeout = '5min'"))
            connection.execute(text('SELECT pg_advisory_xact_lock(814744239)'))
        context.run_migrations()


async def run():
    url = config.attributes.get('database_url') or Settings().database_url
    engine = create_async_engine(url, poolclass=pool.NullPool)
    try:
        async with engine.connect() as connection:
            await connection.run_sync(migrate)
    finally:
        await engine.dispose()


if context.is_offline_mode():
    raise RuntimeError('Use an online connection: legacy schema adoption requires inspection.')
asyncio.run(run())
