from uuid import uuid4
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.schema import CreateSchema, DropSchema
from backend.app.db.config import DatabaseSettings


def test_migration_empty_database_and_repeated_upgrade():
    engine = create_engine(DatabaseSettings().url)
    schema = 'test_migration_' + uuid4().hex
    with engine.begin() as connection:
        connection.execute(CreateSchema(schema))
    try:
        with engine.connect() as connection:
            connection.execute(text(f'SET search_path TO {schema},public'))
            connection.commit()
            config = Config('alembic.ini')
            config.attributes['connection'] = connection
            command.upgrade(config,'head')
            command.upgrade(config,'head')
            assert connection.execute(text('SELECT version_num FROM alembic_version')).scalar_one() == '20261011_01'
            assert 'orders' in inspect(connection).get_table_names(schema=schema)
            connection.execute(text('DELETE FROM alembic_version'))
            connection.execute(text('ALTER TABLE users DROP COLUMN password_hash'))
            connection.execute(text('ALTER TABLE orders DROP COLUMN remark'))
            connection.commit()
            command.upgrade(config,'head')
            assert 'password_hash' in {c['name'] for c in inspect(connection).get_columns('users',schema=schema)}
            assert 'remark' in {c['name'] for c in inspect(connection).get_columns('orders',schema=schema)}
    finally:
        with engine.begin() as connection:
            connection.execute(DropSchema(schema,cascade=True))
        engine.dispose()
