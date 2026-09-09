"""SQLite 备份、校验和恢复测试。"""

import sqlite3
from pathlib import Path

import pytest

from app.backup import BackupError, create_backup, restore_backup, verify_backup
from app.database import database_process_lock


def _create_ledger(path: Path, value: str) -> sqlite3.Connection:
    """创建一个最小账本并保持连接打开。

    Args:
        path: SQLite 文件路径。
        value: 写入的测试值。

    Returns:
        仍保持打开的 SQLite 连接。
    """

    connection = sqlite3.connect(path)
    connection.execute("CREATE TABLE entries (value TEXT NOT NULL)")
    connection.execute("INSERT INTO entries VALUES (?)", (value,))
    connection.commit()
    return connection


def _read_value(path: Path) -> str:
    """读取最小账本中的测试值。

    Args:
        path: SQLite 文件路径。

    Returns:
        数据库保存的测试值。
    """

    with sqlite3.connect(path) as connection:
        return connection.execute("SELECT value FROM entries").fetchone()[0]


def test_create_backup_while_source_connection_is_open(tmp_path: Path) -> None:
    """验证服务持有连接时仍可生成经过校验的一致快照。"""

    database = tmp_path / "data" / "ledger.sqlite3"
    database.parent.mkdir()
    connection = _create_ledger(database, "已提交")

    backup = create_backup(database, tmp_path / "backups")
    verify_backup(backup)

    assert backup.name.startswith("pocket-tally-")
    assert _read_value(backup) == "已提交"
    connection.close()


def test_restore_keeps_pre_restore_snapshot(tmp_path: Path) -> None:
    """验证恢复会替换账本并自动保留恢复前快照。"""

    database = tmp_path / "data" / "ledger.sqlite3"
    database.parent.mkdir()
    connection = _create_ledger(database, "备份版本")
    connection.close()
    backup = create_backup(database, tmp_path / "backups")

    with sqlite3.connect(database) as changed:
        changed.execute("UPDATE entries SET value = '当前版本'")
        changed.commit()

    restored, previous = restore_backup(
        database,
        tmp_path / "backups",
        backup.name,
        confirmed=True,
    )

    assert restored == database.resolve()
    assert previous is not None
    assert previous.name.startswith("pre-restore-")
    assert _read_value(database) == "备份版本"
    assert _read_value(previous) == "当前版本"


def test_corrupt_backup_is_rejected_without_changing_database(
    tmp_path: Path,
) -> None:
    """验证损坏备份不会改写当前账本。"""

    database = tmp_path / "ledger.sqlite3"
    connection = _create_ledger(database, "保持不变")
    connection.close()
    backup_directory = tmp_path / "backups"
    backup_directory.mkdir()
    corrupt = backup_directory / "corrupt.sqlite3"
    corrupt.write_bytes(b"not a sqlite database")

    with pytest.raises(BackupError, match="完整性检查失败"):
        restore_backup(
            database,
            backup_directory,
            corrupt.name,
            confirmed=True,
        )

    assert _read_value(database) == "保持不变"
    assert list(backup_directory.glob("pre-restore-*.sqlite3")) == []


def test_restore_requires_confirmation_and_safe_filename(tmp_path: Path) -> None:
    """验证恢复必须显式确认且不能越过备份目录。"""

    database = tmp_path / "ledger.sqlite3"
    connection = _create_ledger(database, "当前版本")
    connection.close()
    backup_directory = tmp_path / "backups"
    backup_directory.mkdir()

    with pytest.raises(BackupError, match="--confirm"):
        restore_backup(
            database,
            backup_directory,
            "backup.sqlite3",
            confirmed=False,
        )
    with pytest.raises(BackupError, match="不含路径"):
        restore_backup(
            database,
            backup_directory,
            "../backup.sqlite3",
            confirmed=True,
        )


def test_restore_rejects_database_held_by_service(tmp_path: Path) -> None:
    """验证后端持有账本进程锁时拒绝恢复。"""

    database = tmp_path / "ledger.sqlite3"
    connection = _create_ledger(database, "当前版本")
    connection.close()
    backup = create_backup(database, tmp_path / "backups")
    with (
        database_process_lock(database),
        pytest.raises(BackupError, match="先停止后端"),
    ):
        restore_backup(
            database,
            tmp_path / "backups",
            backup.name,
            confirmed=True,
        )

    assert _read_value(database) == "当前版本"
