"""SQLite Engine 创建、进程锁与数据库初始化。"""

import fcntl
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import BinaryIO

from sqlalchemy import URL, Connection, Engine, event, text
from sqlmodel import SQLModel, create_engine

import app.models  # noqa: F401  # 注册 SQLModel 表元数据。
from app.models import Category, CategoryPurpose, new_id


@dataclass(frozen=True, slots=True)
class DefaultCategory:
    """描述全新账本应创建的一个默认分类。"""

    name: str
    purpose: CategoryPurpose
    icon_name: str
    icon_color: str


DEFAULT_CATEGORIES = (
    DefaultCategory("工资", CategoryPurpose.INCOME, "i-lucide-briefcase", "#005CAF"),
    DefaultCategory("奖金", CategoryPurpose.INCOME, "i-lucide-gift", "#FFA400"),
    DefaultCategory("兼职副业", CategoryPurpose.INCOME, "i-lucide-laptop", "#6F5C9A"),
    DefaultCategory(
        "投资收益",
        CategoryPurpose.INCOME,
        "i-lucide-chart-no-axes-combined",
        "#42602D",
    ),
    DefaultCategory(
        "其他收入",
        CategoryPurpose.INCOME,
        "i-lucide-circle-ellipsis",
        "#48929B",
    ),
    DefaultCategory("餐饮", CategoryPurpose.EXPENSE, "i-lucide-utensils", "#C73E3A"),
    DefaultCategory("交通", CategoryPurpose.EXPENSE, "i-lucide-bus", "#005CAF"),
    DefaultCategory("住房", CategoryPurpose.EXPENSE, "i-lucide-house", "#A86F4C"),
    DefaultCategory(
        "生活缴费",
        CategoryPurpose.EXPENSE,
        "i-lucide-receipt-text",
        "#FFA400",
    ),
    DefaultCategory(
        "购物",
        CategoryPurpose.EXPENSE,
        "i-lucide-shopping-bag",
        "#6F5C9A",
    ),
    DefaultCategory(
        "娱乐",
        CategoryPurpose.EXPENSE,
        "i-lucide-gamepad-2",
        "#48929B",
    ),
    DefaultCategory(
        "医疗",
        CategoryPurpose.EXPENSE,
        "i-lucide-heart-pulse",
        "#C73E3A",
    ),
    DefaultCategory(
        "教育",
        CategoryPurpose.EXPENSE,
        "i-lucide-graduation-cap",
        "#42602D",
    ),
    DefaultCategory(
        "通讯网络",
        CategoryPurpose.EXPENSE,
        "i-lucide-smartphone",
        "#005CAF",
    ),
    DefaultCategory("旅行", CategoryPurpose.EXPENSE, "i-lucide-plane", "#48929B"),
    DefaultCategory(
        "人情往来",
        CategoryPurpose.EXPENSE,
        "i-lucide-handshake",
        "#A86F4C",
    ),
    DefaultCategory(
        "其他支出",
        CategoryPurpose.EXPENSE,
        "i-lucide-circle-ellipsis",
        "#6F5C9A",
    ),
)

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
    AFTER UPDATE OF name, purpose, description, parent_category_id, icon_color, icon_name
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
                    description, category, refund_of_transaction_id,
                    balance_adjustment_direction, is_void, voided_at, occurred_at
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

REQUIRED_INDEXES = (
    (
        "CREATE INDEX IF NOT EXISTS ix_transactions_type_status_refund_of "
        "ON transactions (type, is_void, refund_of_transaction_id)"
    ),
)


class DatabaseLockError(RuntimeError):
    """表示同一个 SQLite 账本已被另一个服务进程占用。"""


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


@contextmanager
def database_process_lock(database_path: Path) -> Iterator[BinaryIO]:
    """在服务运行或恢复期间独占一个账本的进程锁。

    Args:
        database_path: 需要保护的 SQLite 数据库路径。

    Yields:
        持有排他锁的锁文件。

    Raises:
        DatabaseLockError: 账本已被另一个进程锁定时抛出。
    """

    database = resolve_database_path(database_path)
    lock_path = Path(f"{database}.lock")
    lock_file = lock_path.open("a+b")
    try:
        try:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise DatabaseLockError(
                "账本正在被 PocketTally 服务使用，请先停止后端"
            ) from error
        yield lock_file
    finally:
        try:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
        finally:
            lock_file.close()


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


def _seed_default_categories(connection: Connection) -> None:
    """在当前初始化事务中写入完整的默认分类集合。

    Args:
        connection: 已持有 SQLite 初始化写锁的数据库连接。
    """

    # 使用相邻但不同的时间戳，在不增加排序字段的前提下保留产品定义顺序。
    seed_time = datetime.now(UTC).replace(tzinfo=None) - timedelta(
        microseconds=len(DEFAULT_CATEGORIES)
    )
    rows = [
        {
            "id": new_id(),
            "name": item.name,
            "purpose": item.purpose,
            "description": None,
            "parent_category_id": None,
            "icon_color": item.icon_color,
            "icon_name": item.icon_name,
            "created_at": seed_time + timedelta(microseconds=index),
            "updated_at": seed_time + timedelta(microseconds=index),
        }
        for index, item in enumerate(DEFAULT_CATEGORIES)
    ]
    connection.execute(Category.__table__.insert(), rows)


def initialize_database(engine: Engine) -> None:
    """原子创建运行时模式，并仅为全新数据库预置默认分类。

    Args:
        engine: 待初始化的 SQLite Engine。

    Raises:
        RuntimeError: 数据库包含不受支持的旧余额触发器时抛出。
    """

    with engine.connect() as connection:
        # 先取得写锁，使并发初始化按顺序判断数据库是否为全新状态。
        connection.exec_driver_sql("BEGIN IMMEDIATE")
        table_names = set(
            connection.execute(
                text("SELECT name FROM sqlite_master WHERE type = 'table'")
            ).scalars()
        )
        is_new_database = not table_names.intersection(SQLModel.metadata.tables)
        trigger_names = set(
            connection.execute(
                text("SELECT name FROM sqlite_master WHERE type = 'trigger'")
            ).scalars()
        )
        try:
            legacy_triggers = trigger_names.intersection(LEGACY_BALANCE_TRIGGERS)
            if legacy_triggers:
                names = ", ".join(sorted(legacy_triggers))
                raise RuntimeError(
                    f"数据库包含旧余额触发器：{names}；请使用新的开发数据库"
                )

            SQLModel.metadata.create_all(connection)
            for statement in REQUIRED_INDEXES:
                connection.exec_driver_sql(statement)
            for statement in UPDATED_AT_TRIGGERS:
                connection.exec_driver_sql(statement)
            if is_new_database:
                _seed_default_categories(connection)
            connection.commit()
        except BaseException:
            connection.rollback()
            raise


__all__ = (
    "DEFAULT_CATEGORIES",
    "LEGACY_BALANCE_TRIGGERS",
    "REQUIRED_INDEXES",
    "DatabaseLockError",
    "create_database_engine",
    "database_process_lock",
    "initialize_database",
    "resolve_database_path",
)
