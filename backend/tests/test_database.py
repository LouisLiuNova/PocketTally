"""运行时 SQLite Engine 和请求级 Session 测试。"""

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from fastapi import HTTPException
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, SQLModel, select

from app.config import Settings
from app.database import (
    DEFAULT_CATEGORIES,
    LEGACY_BALANCE_TRIGGERS,
    create_database_engine,
    initialize_database,
)
from app.dependencies import SessionDep
from app.main import create_app
from app.models import Account, AccountType, Category, CategoryPurpose


def default_category_names() -> set[str]:
    """返回默认分类名称集合，避免测试重复维护清单。"""

    return {name for name, _purpose in DEFAULT_CATEGORIES}


def test_database_initialization_seeds_default_categories_idempotently(
    tmp_path: Path,
) -> None:
    """验证新数据库预置正确用途的一级分类且重复初始化不重复写入。"""

    engine = create_database_engine(tmp_path / "default-categories.sqlite3")
    initialize_database(engine)
    with Session(engine) as session:
        categories = session.exec(select(Category)).all()
        assert {category.name for category in categories} == default_category_names()
        assert {
            (category.name, category.purpose)
            for category in categories
        } == set(DEFAULT_CATEGORIES)
        assert all(category.parent_category_id is None for category in categories)

    initialize_database(engine)
    with Session(engine) as session:
        assert len(session.exec(select(Category)).all()) == len(DEFAULT_CATEGORIES)
    engine.dispose()


def test_database_initialization_does_not_fill_existing_category_data(
    tmp_path: Path,
) -> None:
    """验证已有分类的数据库不会被自动补齐默认分类。"""

    database_path = tmp_path / "existing-categories.sqlite3"
    engine = create_database_engine(database_path)
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        session.add(Category(name="自定义分类", purpose=CategoryPurpose.EXPENSE))
        session.commit()

    initialize_database(engine)
    with Session(engine) as session:
        categories = session.exec(select(Category)).all()
        assert [category.name for category in categories] == ["自定义分类"]
    engine.dispose()


def test_database_initialization_rolls_back_partial_default_seed(
    tmp_path: Path,
) -> None:
    """验证默认分类批量写入失败时不会留下半套分类。"""

    engine = create_database_engine(tmp_path / "default-categories-rollback.sqlite3")
    SQLModel.metadata.create_all(engine)
    with engine.begin() as connection:
        connection.exec_driver_sql(
            "CREATE TRIGGER abort_default_category_seed "
            "BEFORE INSERT ON categories "
            "WHEN NEW.name = '餐饮' "
            "BEGIN SELECT RAISE(ABORT, '测试默认分类写入失败'); END"
        )

    with pytest.raises(IntegrityError, match="测试默认分类写入失败"):
        initialize_database(engine)

    with Session(engine) as session:
        assert session.exec(select(Category)).all() == []

    with engine.begin() as connection:
        connection.exec_driver_sql("DROP TRIGGER abort_default_category_seed")
    initialize_database(engine)
    engine.dispose()


def test_database_initialization_is_safe_when_called_concurrently(
    tmp_path: Path,
) -> None:
    """验证并发初始化最终只生成一套默认分类。"""

    database_path = tmp_path / "concurrent-default-categories.sqlite3"
    setup_engine = create_database_engine(database_path)
    SQLModel.metadata.create_all(setup_engine)
    with setup_engine.begin() as connection:
        connection.execute(text("DELETE FROM categories"))
    setup_engine.dispose()

    engines = [create_database_engine(database_path) for _ in range(2)]
    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            list(executor.map(initialize_database, engines))

        with Session(engines[0]) as session:
            categories = session.exec(select(Category)).all()
            assert len(categories) == len(DEFAULT_CATEGORIES)
            assert {category.name for category in categories} == default_category_names()
    finally:
        for engine in engines:
            engine.dispose()


def test_database_initialization_is_repeatable_and_enables_foreign_keys(
    tmp_path: Path,
) -> None:
    """验证新数据库可重复初始化、持久化数据并为每个连接启用外键。"""

    database_path = tmp_path / "nested" / "runtime.sqlite3"
    engine = create_database_engine(database_path)
    initialize_database(engine)
    with Session(engine) as session:
        session.add(Account(type=AccountType.CREDIT, name="持久账户"))
        session.commit()
    initialize_database(engine)
    engine.dispose()

    reopened_engine = create_database_engine(database_path)
    with Session(reopened_engine) as session:
        assert session.exec(select(Account)).one().name == "持久账户"
        assert session.exec(text("PRAGMA foreign_keys")).one() == (1,)
    reopened_engine.dispose()


def test_database_initialization_restores_statistics_index(tmp_path: Path) -> None:
    """验证已有账本会幂等补建有效退款统计索引。"""

    engine = create_database_engine(tmp_path / "existing.sqlite3")
    initialize_database(engine)
    with engine.begin() as connection:
        connection.exec_driver_sql(
            "DROP INDEX ix_transactions_type_status_refund_of"
        )

    initialize_database(engine)
    with engine.connect() as connection:
        index_names = {
            row[1]
            for row in connection.exec_driver_sql(
                "PRAGMA index_list(transactions)"
            )
        }
        query_plan = " ".join(
            str(row[3])
            for row in connection.exec_driver_sql(
                "EXPLAIN QUERY PLAN "
                "SELECT refund_of_transaction_id, SUM(amount_minor) "
                "FROM transactions "
                "WHERE type = 'expense_refund' AND is_void = 0 "
                "GROUP BY refund_of_transaction_id"
            )
        )
    engine.dispose()

    assert "ix_transactions_type_status_refund_of" in index_names
    assert "ix_transactions_type_status_refund_of" in query_plan


def test_database_rejects_legacy_balance_triggers(tmp_path: Path) -> None:
    """验证运行时不会静默升级带旧余额触发器的数据库。"""

    engine = create_database_engine(tmp_path / "legacy.sqlite3")
    initialize_database(engine)
    with engine.begin() as connection:
        connection.exec_driver_sql(
            "CREATE TRIGGER tr_accounts_rebuild_amount_projection "
            "AFTER UPDATE OF amount_minor ON accounts BEGIN SELECT 1; END"
        )

    with pytest.raises(RuntimeError, match="旧余额触发器"):
        initialize_database(engine)
    engine.dispose()


@pytest.mark.asyncio
async def test_request_session_commits_and_rolls_back(tmp_path: Path) -> None:
    """验证请求成功提交、处理失败回滚且不同请求使用不同 Session。"""

    app = create_app(
        Settings(environment="test", database_path=tmp_path / "requests.sqlite3")
    )
    request_sessions: list[Session] = []

    @app.post("/test/accounts/{name}")
    def create_account(name: str, session: SessionDep) -> dict[str, str]:
        """创建用于验证提交行为的账户。"""

        request_sessions.append(session)
        session.add(Account(type=AccountType.CREDIT, name=name))
        return {"name": name}

    @app.post("/test/rollback/{name}")
    def rollback_account(name: str, session: SessionDep) -> None:
        """写入账户后主动触发用于验证回滚的错误。"""

        session.add(Account(type=AccountType.CREDIT, name=name))
        session.flush()
        raise HTTPException(status_code=409, detail="测试回滚")

    async with (
        app.router.lifespan_context(app),
        AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client,
    ):
        assert (await client.post("/test/accounts/成功账户")).status_code == 200
        assert (await client.post("/test/accounts/另一账户")).status_code == 200
        assert (await client.post("/test/rollback/回滚账户")).status_code == 409

        with Session(app.state.resources.engine) as verification_session:
            names = {
                account.name for account in verification_session.exec(select(Account))
            }
            assert names == {"成功账户", "另一账户"}

    assert request_sessions[0] is not request_sessions[1]


@pytest.mark.asyncio
async def test_commit_failure_is_raised_before_response(tmp_path: Path) -> None:
    """验证依赖提交失败不会返回成功，也不会留下无效账户。"""

    database_path = tmp_path / "commit-failure.sqlite3"
    app = create_app(Settings(environment="test", database_path=database_path))

    @app.post("/test/invalid-account")
    def create_invalid_account(session: SessionDep) -> dict[str, bool]:
        """暂存一个将在提交阶段违反约束的账户。"""

        session.add(
            Account(type=AccountType.DEBIT, name="无效账户", amount_minor=-1)
        )
        return {"created": True}

    async with (
        app.router.lifespan_context(app),
        AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client,
    ):
        with pytest.raises(IntegrityError):
            await client.post("/test/invalid-account")

        with Session(app.state.resources.engine) as verification_session:
            assert verification_session.exec(select(Account)).all() == []


def test_runtime_schema_has_only_audit_triggers(tmp_path: Path) -> None:
    """验证运行时模式不包含余额业务触发器。"""

    engine = create_database_engine(tmp_path / "triggers.sqlite3")
    initialize_database(engine)
    with engine.connect() as connection:
        trigger_names = set(
            connection.execute(
                text("SELECT name FROM sqlite_master WHERE type = 'trigger'")
            ).scalars()
        )
    engine.dispose()

    assert trigger_names.isdisjoint(LEGACY_BALANCE_TRIGGERS)
    assert {
        "tr_accounts_updated_at",
        "tr_categories_updated_at",
        "tr_tags_updated_at",
        "tr_transactions_updated_at",
    }.issubset(trigger_names)


def test_account_update_preserves_created_at(tmp_path: Path) -> None:
    """验证业务更新只刷新更新时间，不改写创建时间。"""

    engine = create_database_engine(tmp_path / "timestamps.sqlite3")
    initialize_database(engine)
    with engine.begin() as connection:
        connection.exec_driver_sql(
            "INSERT INTO accounts (id, type, name, created_at, updated_at) "
            "VALUES ('account-1', 'credit', '原名称', "
            "'2000-01-01 00:00:00', '2000-01-01 00:00:00')"
        )
        connection.exec_driver_sql(
            "UPDATE accounts SET name = '新名称' WHERE id = 'account-1'"
        )
        created_at, updated_at = connection.exec_driver_sql(
            "SELECT created_at, updated_at FROM accounts WHERE id = 'account-1'"
        ).one()
    engine.dispose()

    assert str(created_at) == "2000-01-01 00:00:00"
    assert str(updated_at) != "2000-01-01 00:00:00"
