"""迁移的历史基线、故障回滚与恢复验证。"""

from pathlib import Path

import pytest
from sqlalchemy import text
from sqlmodel import Session

from app.database import create_database_engine, initialize_database
from app.models import Account, AccountType


def legacy_engine(path: Path):
    engine = create_database_engine(path)
    with engine.connect() as c:
        c.connection.driver_connection.executescript(
            (Path(__file__).parents[1] / "db/schema.sql")
            .read_text()
            .split("-- 导入审计模型")[0]
        )
    return engine


def test_legacy_upgrade_preserves_data_and_backup(tmp_path):
    engine = legacy_engine(tmp_path / "legacy.sqlite3")
    with Session(engine) as s, s.begin():
        s.add(Account(type=AccountType.CREDIT, name="历史账户"))
    initialize_database(engine)
    with Session(engine) as s:
        assert s.exec(text("SELECT version_num FROM alembic_version")).one() == (
            "0002",
        )
        assert s.exec(text("SELECT name FROM accounts")).one() == ("历史账户",)
        assert s.exec(text("PRAGMA foreign_key_check")).all() == []
        assert s.exec(text("SELECT COUNT(*) FROM categories")).one() == (0,)
    backups = list((tmp_path / "migration-backups").glob("*.sqlite3"))
    assert len(backups) == 1
    from app.backup import verify_backup

    verify_backup(backups[0])
    initialize_database(engine)
    assert len(list((tmp_path / "migration-backups").glob("*.sqlite3"))) == 1
    engine.dispose()


def test_unknown_structure_and_version_rejected(tmp_path):
    engine = legacy_engine(tmp_path / "unknown.sqlite3")
    with engine.begin() as c:
        c.exec_driver_sql("ALTER TABLE accounts ADD COLUMN unexpected TEXT")
    with pytest.raises(RuntimeError, match="基线"):
        initialize_database(engine)
    engine.dispose()
    engine = create_database_engine(tmp_path / "future.sqlite3")
    initialize_database(engine)
    with engine.begin() as c:
        c.exec_driver_sql("UPDATE alembic_version SET version_num = '9999'")
    with pytest.raises(RuntimeError, match="版本"):
        initialize_database(engine)
    engine.dispose()


def test_failed_upgrade_leaves_legacy_unchanged(tmp_path, monkeypatch):
    engine = legacy_engine(tmp_path / "failure.sqlite3")
    from alembic.operations import Operations

    original = Operations.execute

    def fail(self, sqltext, **kwargs):
        if "CREATE TABLE import_rows" in str(sqltext):
            raise RuntimeError("故障注入")
        return original(self, sqltext, **kwargs)

    with monkeypatch.context() as m:
        m.setattr(Operations, "execute", fail)
        with pytest.raises(RuntimeError, match="故障"):
            initialize_database(engine)
    with engine.connect() as c:
        names = {
            r[0]
            for r in c.exec_driver_sql(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
    assert "alembic_version" not in names
    assert "import_batches" not in names
    assert list((tmp_path / "migration-backups").glob("*.sqlite3"))
    initialize_database(engine)
    engine.dispose()


def test_upgrade_backup_can_restore_legacy_data(tmp_path):
    """停止连接后恢复升级前备份，账本回到无版本基线且数据完整。"""
    from app.backup import restore_backup

    path = tmp_path / "restore.sqlite3"
    engine = legacy_engine(path)
    with Session(engine) as session, session.begin():
        session.add(Account(type=AccountType.CREDIT, name="恢复账户"))
    initialize_database(engine)
    engine.dispose()
    directory = tmp_path / "migration-backups"
    backup = next(directory.glob("*.sqlite3"))
    restored, previous = restore_backup(path, directory, backup.name, confirmed=True)
    assert restored == path and previous is not None
    engine = create_database_engine(path)
    with engine.connect() as connection:
        names = {
            r[0]
            for r in connection.exec_driver_sql(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
        assert "alembic_version" not in names and "import_batches" not in names
        assert (
            connection.exec_driver_sql("SELECT name FROM accounts").scalar()
            == "恢复账户"
        )
    initialize_database(engine)
    engine.dispose()
