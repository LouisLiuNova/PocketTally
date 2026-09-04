"""运行时 SQLite Engine 和请求级 Session 测试。"""

from pathlib import Path

import pytest
from fastapi import HTTPException
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.config import Settings
from app.database import (
    LEGACY_BALANCE_TRIGGERS,
    create_database_engine,
    initialize_database,
)
from app.dependencies import SessionDep
from app.main import create_app
from app.models import Account, AccountType


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
