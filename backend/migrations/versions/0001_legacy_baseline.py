"""Create or adopt the frozen legacy application schema without deleting data."""
from alembic import op
from sqlalchemy import inspect
from pgvector.sqlalchemy import Vector  # register the PostgreSQL reflection type

from migrations.legacy_schema import Base

revision = '0001_legacy_baseline'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    connection = op.get_bind()
    inspector = inspect(connection)
    for table in Base.metadata.sorted_tables:
        if inspector.has_table(table.name):
            present = {column['name'] for column in inspector.get_columns(table.name)}
            missing = set(table.columns.keys()) - present
            if missing:
                raise RuntimeError(f'Legacy table {table.name} lacks required columns: {sorted(missing)}')
    Base.metadata.create_all(connection, checkfirst=True)


def downgrade():
    raise RuntimeError('Baseline is forward-only: roll back the application image or restore a verified backup into a separate database.')
