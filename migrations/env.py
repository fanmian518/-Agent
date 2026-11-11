from alembic import context
from backend.app.db.database import get_engine
from backend.app.db.models import Base


def migrate(connection):
    context.configure(connection=connection, target_metadata=Base.metadata, compare_type=True)
    with context.begin_transaction():
        context.run_migrations()


if context.is_offline_mode():
    raise RuntimeError('This baseline inspects existing installations; run upgrade online.')
elif context.config.attributes.get('connection') is not None:
    migrate(context.config.attributes['connection'])
else:
    with get_engine().connect() as connection:
        migrate(connection)
