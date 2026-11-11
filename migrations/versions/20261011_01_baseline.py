"""Versioned baseline supporting empty databases and the legacy initializer."""
from alembic import op
from sqlalchemy import MetaData, inspect, text
from migrations.schema_v1 import Base

revision = '20261011_01'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    connection = op.get_bind()
    # Frozen snapshot, never imported from live models.
    connection.execute(text('CREATE EXTENSION IF NOT EXISTS vector'))
    schema = connection.execute(text('SELECT current_schema()')).scalar_one()
    metadata = MetaData()
    for table in Base.metadata.sorted_tables:
        table.to_metadata(metadata, schema=schema)
    metadata.create_all(connection)
    legacy_columns = {'users': ['password_hash'], 'orders': ['address_id', 'remark', 'refund_reason', 'refund_status', 'confirmed_at']}
    inspector = inspect(connection)
    for table_name, names in legacy_columns.items():
        existing = {column['name'] for column in inspector.get_columns(table_name, schema=schema)}
        for name in names:
            if name not in existing:
                op.add_column(table_name, Base.metadata.tables[table_name].c[name]._copy(), schema=schema)


def downgrade():
    raise RuntimeError('Baseline downgrade is disabled: restore a verified database backup instead.')
