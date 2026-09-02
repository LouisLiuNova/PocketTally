"""SQLite 数据模型的完整性与 ORM 同步测试。"""

import sqlite3
from pathlib import Path

import pytest
from sqlalchemy import CheckConstraint, create_engine
from sqlmodel import SQLModel

import app.models

SCHEMA_PATH = Path(__file__).parents[1] / "db" / "schema.sql"


def create_connection() -> sqlite3.Connection:
    """创建已加载项目 SQLite DDL 的内存连接。

    Returns:
        已启用外键并已建表的内存 SQLite 连接。
    """

    connection = sqlite3.connect(":memory:")
    connection.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
    return connection


def test_schema_normalizes_tags_and_enforces_unique_names() -> None:
    """验证标签关联、外键和不区分大小写的名称唯一性。"""

    connection = create_connection()
    try:
        connection.execute(
            "INSERT INTO accounts (id, type, name) VALUES ('account-1', 'credit', 'Wallet')"
        )
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                "INSERT INTO accounts (id, type, name) VALUES ('account-2', 'debit', 'wallet')"
            )

        connection.execute("INSERT INTO categories (id, name) VALUES ('category-1', '餐饮')")
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                "INSERT INTO categories (id, name) VALUES ('category-2', '餐饮')"
            )

        connection.execute("INSERT INTO tags (id, name) VALUES ('tag-1', '外卖')")
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute("INSERT INTO tags (id, name) VALUES ('tag-2', '外卖')")

        connection.execute(
            """
            INSERT INTO transactions (
                id, type, src_account_id, amount_minor, category, occurred_at
            ) VALUES ('transaction-1', 'expense', 'account-1', 1200, 'category-1',
                      '2026-08-24 12:00:00')
            """
        )
        connection.execute(
            "INSERT INTO transaction_tags (transaction_id, tag_id) VALUES ('transaction-1', 'tag-1')"
        )
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                "INSERT INTO transaction_tags (transaction_id, tag_id) VALUES ('transaction-1', 'tag-1')"
            )
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                "INSERT INTO transaction_tags (transaction_id, tag_id) VALUES ('transaction-1', 'missing-tag')"
            )

        transaction_columns = {
            row[1] for row in connection.execute("PRAGMA table_info(transactions)")
        }
        assert "tags" not in transaction_columns
        assert "amount" not in transaction_columns
        assert "amount_minor" in transaction_columns
        assert "occurred_at" in transaction_columns
    finally:
        connection.close()


def test_schema_rejects_unknown_types_and_non_positive_amounts() -> None:
    """验证 SQLite DDL 拒绝未知交易类型和非正金额。"""

    connection = create_connection()
    try:
        connection.execute(
            "INSERT INTO accounts (id, type, name) VALUES ('account-1', 'debit', 'Wallet')"
        )
        connection.execute(
            "INSERT INTO categories (id, name) VALUES ('category-1', '餐饮')"
        )

        base_values = (
            "'transaction-1', 'expense', 'account-1', 1, 'category-1', "
            "'2026-08-24 12:00:00'"
        )
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                "INSERT INTO transactions "
                "(id, type, src_account_id, amount_minor, category, occurred_at) "
                f"VALUES ({base_values.replace("'expense'", "'unknown'")})"
            )
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                "INSERT INTO transactions "
                "(id, type, src_account_id, amount_minor, category, occurred_at) "
                f"VALUES ({base_values.replace(', 1,', ', 0,')})"
            )
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                "INSERT INTO transactions "
                "(id, type, src_account_id, amount_minor, category, occurred_at) "
                f"VALUES ({base_values.replace(', 1,', ', -1,')})"
            )

        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                "INSERT INTO accounts (id, type, name, amount_minor) "
                "VALUES ('debit-negative', 'debit', 'Negative debit', -1)"
            )
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                "INSERT INTO accounts (id, type, name, amount_minor) "
                "VALUES ('fractional-minor', 'debit', 'Fractional minor', 1.5)"
            )
        connection.execute(
                "INSERT INTO accounts (id, type, name, amount_minor) "
            "VALUES ('credit-negative', 'credit', 'Negative credit', -1)"
        )
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                "INSERT INTO accounts (id, type, name) "
                "VALUES ('unknown-type', 'cash', 'Unknown type')"
            )
    finally:
        connection.close()


def test_schema_server_defaults_and_triggers_keep_audit_values_current() -> None:
    """验证 DDL 默认值与更新时间戳不依赖应用写入路径。"""

    connection = create_connection()
    try:
        connection.execute(
            """
            INSERT INTO accounts (id, type, name, updated_at)
            VALUES ('account-1', 'debit', 'Wallet', '2000-01-01 00:00:00')
            """
        )
        connection.execute("UPDATE accounts SET name = 'Wallet 2' WHERE id = 'account-1'")
        amount_minor, updated_at = connection.execute(
            "SELECT amount_minor, updated_at FROM accounts WHERE id = 'account-1'"
        ).fetchone()

        assert amount_minor == 0
        assert updated_at != "2000-01-01 00:00:00"
    finally:
        connection.close()


def test_schema_rebuilds_balance_projection_from_transactions() -> None:
    """验证余额调整、作废和直接余额改写都以交易记录为准。"""

    connection = create_connection()
    try:
        connection.execute(
            "INSERT INTO accounts (id, type, name) VALUES ('account-1', 'credit', 'Wallet')"
        )
        connection.execute(
            """
            INSERT INTO transactions (
                id, type, src_account_id, amount_minor,
                balance_adjustment_direction, occurred_at
            ) VALUES ('adjustment-1', 'balance_adjustment', 'account-1', 250,
                      'increase', '2026-08-24 12:00:00')
            """
        )
        assert connection.execute(
            "SELECT amount_minor FROM accounts WHERE id = 'account-1'"
        ).fetchone()[0] == 250

        connection.execute(
            "UPDATE transactions SET voided_at = '2026-08-25 12:00:00' "
            "WHERE id = 'adjustment-1'"
        )
        assert connection.execute(
            "SELECT amount_minor FROM accounts WHERE id = 'account-1'"
        ).fetchone()[0] == 0

        connection.execute(
            "UPDATE accounts SET amount_minor = 999 WHERE id = 'account-1'"
        )
        assert connection.execute(
            "SELECT amount_minor FROM accounts WHERE id = 'account-1'"
        ).fetchone()[0] == 0

        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                "INSERT INTO transactions "
                "(id, type, src_account_id, amount_minor, occurred_at) "
                "VALUES ('invalid-adjustment', 'balance_adjustment', 'account-1', "
                "100, '2026-08-24 12:00:00')"
            )
    finally:
        connection.close()


def test_sqlmodel_declares_database_defaults_and_normalized_tag_link() -> None:
    """验证 SQLModel 建表结果保留服务器默认值和关联表主键。"""

    engine = create_engine("sqlite://")
    SQLModel.metadata.create_all(engine)
    with engine.connect() as connection:
        account_columns = {
            row[1]: row[4]
            for row in connection.exec_driver_sql("PRAGMA table_info(accounts)")
        }
        transaction_columns = {
            row[1]: row[4]
            for row in connection.exec_driver_sql("PRAGMA table_info(transactions)")
        }
        transaction_tag_columns = connection.exec_driver_sql(
            "PRAGMA table_info(transaction_tags)"
        ).fetchall()

    assert account_columns["amount_minor"] == "0"
    assert transaction_columns["is_refund"] == "0"
    assert app.models.Account.__table__.c.type.type.enums == ["debit", "credit"]
    assert any(
        isinstance(constraint, CheckConstraint)
        and str(constraint.sqltext) == "amount_minor > 0"
        for constraint in app.models.Transaction.__table__.constraints
    )
    assert any(
        isinstance(constraint, CheckConstraint)
        and str(constraint.sqltext) == "type = 'credit' OR amount_minor >= 0"
        for constraint in app.models.Account.__table__.constraints
    )
    assert {row[1] for row in transaction_tag_columns} == {
        "transaction_id",
        "tag_id",
    }
    assert {row[5] for row in transaction_tag_columns} == {1, 2}
