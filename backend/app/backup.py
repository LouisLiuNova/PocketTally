"""创建、校验和恢复 PocketTally SQLite 备份。"""

import argparse
import os
import sqlite3
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path

from app.config import get_settings
from app.database import DatabaseLockError, database_process_lock, resolve_database_path


class BackupError(RuntimeError):
    """表示备份操作无法安全完成。"""


def _timestamp() -> str:
    """返回适合备份文件名的 UTC 时间戳。

    Returns:
        带微秒的紧凑 UTC 时间戳。
    """

    return datetime.now(UTC).strftime("%Y%m%dT%H%M%S.%fZ")


def _resolve_backup_directory(backup_directory: Path) -> Path:
    """解析并创建备份目录。

    Args:
        backup_directory: 配置的备份目录。

    Returns:
        已创建的绝对备份目录。
    """

    directory = backup_directory.expanduser()
    if not directory.is_absolute():
        directory = Path.cwd() / directory
    directory = directory.resolve()
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def _resolve_backup_file(backup_directory: Path, filename: str) -> Path:
    """把不含路径分隔符的备份文件名解析到备份目录内。

    Args:
        backup_directory: 备份根目录。
        filename: 用户提供的备份文件名。

    Returns:
        备份目录内的绝对文件路径。

    Raises:
        BackupError: 文件名为空、包含路径或不是 SQLite 备份文件时抛出。
    """

    candidate = Path(filename)
    if not filename or candidate.name != filename or candidate.suffix != ".sqlite3":
        raise BackupError("备份文件名必须是不含路径的 .sqlite3 文件名")
    return backup_directory / candidate.name


def verify_backup(path: Path) -> None:
    """以只读方式执行 SQLite 完整性检查。

    Args:
        path: 待校验的 SQLite 文件。

    Raises:
        BackupError: 文件不存在、不是普通文件或完整性检查失败时抛出。
    """

    if not path.is_file():
        raise BackupError(f"备份文件不存在：{path.name}")

    try:
        with sqlite3.connect(f"{path.as_uri()}?mode=ro", uri=True) as connection:
            results = [row[0] for row in connection.execute("PRAGMA integrity_check")]
    except sqlite3.Error as error:
        raise BackupError(f"SQLite 完整性检查失败：{error}") from error

    if results != ["ok"]:
        details = "; ".join(str(result) for result in results)
        raise BackupError(f"SQLite 完整性检查未通过：{details}")


def _copy_database(source: Path, destination: Path) -> None:
    """使用 SQLite 在线备份 API 复制数据库。

    Args:
        source: 源 SQLite 数据库。
        destination: 必须尚不存在的目标文件。

    Raises:
        BackupError: SQLite 无法完成一致快照时抛出。
    """

    try:
        with (
            sqlite3.connect(f"{source.as_uri()}?mode=ro", uri=True) as source_db,
            sqlite3.connect(destination) as destination_db,
        ):
            source_db.backup(destination_db)
    except sqlite3.Error as error:
        raise BackupError(f"SQLite 备份失败：{error}") from error


def create_backup(
    database_path: Path,
    backup_directory: Path,
    *,
    prefix: str = "pocket-tally",
) -> Path:
    """在线创建经过完整性检查的原子备份。

    Args:
        database_path: 当前账本数据库路径。
        backup_directory: 保存备份的目录。
        prefix: 备份文件名前缀。

    Returns:
        新备份文件的绝对路径。

    Raises:
        BackupError: 数据库不存在或备份无法安全创建时抛出。
    """

    database = resolve_database_path(database_path)
    if not database.is_file():
        raise BackupError(f"账本数据库不存在：{database}")
    directory = _resolve_backup_directory(backup_directory)
    destination = directory / f"{prefix}-{_timestamp()}.sqlite3"

    file_descriptor, temporary_name = tempfile.mkstemp(
        prefix=".pocket-tally-backup-", suffix=".tmp", dir=directory
    )
    os.close(file_descriptor)
    temporary = Path(temporary_name)
    temporary.unlink()
    try:
        _copy_database(database, temporary)
        verify_backup(temporary)
        temporary.chmod(0o600)
        os.replace(temporary, destination)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
    return destination


def restore_backup(
    database_path: Path,
    backup_directory: Path,
    filename: str,
    *,
    confirmed: bool,
) -> tuple[Path, Path | None]:
    """校验备份并原子恢复账本，同时保留恢复前快照。

    Args:
        database_path: 待恢复的账本数据库路径。
        backup_directory: 备份根目录。
        filename: 备份目录内的文件名。
        confirmed: 是否显式确认破坏性恢复操作。

    Returns:
        恢复后的数据库路径和可选的恢复前快照路径。

    Raises:
        BackupError: 未确认、服务可能仍在运行或恢复校验失败时抛出。
    """

    if not confirmed:
        raise BackupError("恢复操作必须提供 --confirm")

    directory = _resolve_backup_directory(backup_directory)
    source = _resolve_backup_file(directory, filename)
    verify_backup(source)
    database = resolve_database_path(database_path)

    try:
        with database_process_lock(database):
            companions = [
                Path(f"{database}{suffix}")
                for suffix in ("-journal", "-wal", "-shm")
                if Path(f"{database}{suffix}").exists()
            ]
            if companions:
                names = ", ".join(path.name for path in companions)
                raise BackupError(f"发现活动数据库伴随文件：{names}")

            previous = None
            if database.exists():
                previous = create_backup(
                    database,
                    directory,
                    prefix="pre-restore",
                )

            file_descriptor, temporary_name = tempfile.mkstemp(
                prefix=".pocket-tally-restore-", suffix=".tmp", dir=database.parent
            )
            os.close(file_descriptor)
            temporary = Path(temporary_name)
            temporary.unlink()
            try:
                _copy_database(source, temporary)
                verify_backup(temporary)
                temporary.chmod(0o600)
                os.replace(temporary, database)
            except Exception:
                temporary.unlink(missing_ok=True)
                raise
    except DatabaseLockError as error:
        raise BackupError(str(error)) from error
    return database, previous


def _build_parser() -> argparse.ArgumentParser:
    """构建备份命令行解析器。

    Returns:
        已配置的参数解析器。
    """

    parser = argparse.ArgumentParser(description="PocketTally SQLite 备份工具")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("create", help="在线创建一致备份")

    verify_parser = subparsers.add_parser("verify", help="校验一个备份")
    verify_parser.add_argument("filename", help="备份目录内的文件名")

    restore_parser = subparsers.add_parser("restore", help="离线恢复一个备份")
    restore_parser.add_argument("filename", help="备份目录内的文件名")
    restore_parser.add_argument(
        "--confirm", action="store_true", help="确认替换当前数据库"
    )
    return parser


def main() -> None:
    """执行 PocketTally 备份命令。

    Raises:
        SystemExit: 参数无效或备份操作失败时以非零状态退出。
    """

    arguments = _build_parser().parse_args()
    settings = get_settings()
    try:
        if arguments.command == "create":
            created = create_backup(
                settings.database_path,
                settings.backup_directory,
            )
            print(created.name)
        elif arguments.command == "verify":
            directory = _resolve_backup_directory(settings.backup_directory)
            backup = _resolve_backup_file(directory, arguments.filename)
            verify_backup(backup)
            print(f"备份完整：{backup.name}")
        else:
            restored, previous = restore_backup(
                settings.database_path,
                settings.backup_directory,
                arguments.filename,
                confirmed=arguments.confirm,
            )
            print(f"已恢复：{restored}")
            if previous is not None:
                print(f"恢复前快照：{previous.name}")
    except BackupError as error:
        print(f"错误：{error}", file=sys.stderr)
        raise SystemExit(1) from error


if __name__ == "__main__":
    main()
