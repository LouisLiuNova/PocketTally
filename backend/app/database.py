"""SQLite Engine 创建与数据库初始化。"""

from pathlib import Path

from sqlalchemy import URL, Engine, event, text
from sqlmodel import SQLModel, create_engine

import app.models  # noqa: F401  # 注册 SQLModel 表元数据。

LEGACY_BALANCE_TRIGGERS = (
    "tr_transactions_sync_account_balances_insert",
    "tr_transactions_sync_account_balances_update",
    "tr_transactions_sync_account_balances_delete",
    "tr_accounts_rebuild_amount_projection",
)

UPDATED_AT_TRIGGERS = (
    """
    CREATE TRIGGER IF NOT EXISTS tr_accounts_updated_at
    AFTER UPDATE OF type, name, card_number, description, amount_minor ON accounts
    FOR EACH ROW BEGIN
        UPDATE accounts SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
    END
    """,
    """
    CREATE TRIGGER IF NOT EXISTS tr_categories_updated_at
    AFTER UPDATE OF name, description, parent_category_id, icon_color, icon_name
    ON categories
    FOR EACH ROW BEGIN
        UPDATE categories SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
    END
    """,
    """
    CREATE TRIGGER IF NOT EXISTS tr_tags_updated_at
    AFTER UPDATE OF name, description, color ON tags
    FOR EACH ROW BEGIN
        UPDATE tags SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
    END
    """,
    """
    CREATE TRIGGER IF NOT EXISTS tr_transactions_updated_at
    AFTER UPDATE OF type, src_account_id, dest_account_id, amount_minor,
                    description, category, is_refund, related_transaction_id,
                    balance_adjustment_direction, voided_at, occurred_at
    ON transactions
    FOR EACH ROW BEGIN
        UPDATE transactions SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
    END
    """,
    """
    CREATE TRIGGER IF NOT EXISTS tr_transaction_tags_insert_updated_at
    AFTER INSERT ON transaction_tags
    FOR EACH ROW BEGIN
        UPDATE transactions SET updated_at = CURRENT_TIMESTAMP
        WHERE id = NEW.transaction_id;
    END
    """,
    """
    CREATE TRIGGER IF NOT EXISTS tr_transaction_tags_delete_updated_at
    AFTER DELETE ON transaction_tags
    FOR EACH ROW BEGIN
        UPDATE transactions SET updated_at = CURRENT_TIMESTAMP
        WHERE id = OLD.transaction_id;
    END
    """,
)


def resolve_database_path(database_path: Path) -> Path:
    """解析并准备本地 SQLite 数据库路径。

    Args:
        database_path: 配置中的绝对或相对路径。

    Returns:
        已展开并转为绝对形式的数据库路径。
    """

    path = database_path.expanduser()
    if not path.is_absolute():
        path = Path.cwd() / path
    path = path.resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def create_database_engine(database_path: Path) -> Engine:
    """创建为 FastAPI 同步会话配置的 SQLite Engine。

    Args:
        database_path: 本地 SQLite 数据库路径。

    Returns:
        已注册连接级外键检查的 Engine。

    Raises:
        RuntimeError: SQLite 连接无法启用外键约束时抛出。
    """

    path = resolve_database_path(database_path)
    engine = create_engine(
        URL.create("sqlite", database=str(path)),
        connect_args={"check_same_thread": False},
    )

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(dbapi_connection, _connection_record) -> None:
        """启用并验证当前 SQLite 物理连接的外键约束。"""

        cursor = dbapi_connection.cursor()
        try:
            cursor.execute("PRAGMA foreign_keys = ON")
            cursor.execute("PRAGMA foreign_keys")
            result = cursor.fetchone()
        finally:
            cursor.close()
        if result != (1,):
            raise RuntimeError("SQLite 连接无法启用外键约束")

    return engine


def initialize_database(engine: Engine) -> None:
    """创建表和审计触发器，并拒绝带旧余额触发器的数据库。

    Args:
        engine: 待初始化的 SQLite Engine。

    Raises:
        RuntimeError: 数据库包含不受支持的旧余额触发器时抛出。
    """

    with engine.connect() as connection:
        trigger_names = set(
            connection.execute(
                text("SELECT name FROM sqlite_master WHERE type = 'trigger'")
            ).scalars()
        )
    legacy_triggers = trigger_names.intersection(LEGACY_BALANCE_TRIGGERS)
    if legacy_triggers:
        names = ", ".join(sorted(legacy_triggers))
        raise RuntimeError(
            f"数据库包含旧余额触发器：{names}；请使用新的开发数据库"
        )

    SQLModel.metadata.create_all(engine)
    with engine.begin() as connection:
        for statement in UPDATED_AT_TRIGGERS:
            connection.exec_driver_sql(statement)


__all__ = (
    "LEGACY_BALANCE_TRIGGERS",
    "create_database_engine",
    "initialize_database",
    "resolve_database_path",
)
