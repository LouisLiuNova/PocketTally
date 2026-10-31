"""在启动者已持有的 SQLite 事务中执行 Alembic。"""

from alembic import context

connection = context.config.attributes["connection"]
context.configure(connection=connection, transactional_ddl=True, render_as_batch=True)
with context.begin_transaction():
    context.run_migrations()
