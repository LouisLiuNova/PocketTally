"""已发布账本的结构识别、备份与顺序迁移。"""

import re
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import Connection, inspect

CORE_TABLES = {"accounts", "categories", "tags", "transactions", "transaction_tags"}


def schema_signature(connection: Connection) -> dict:
    """忽略约束名称与索引，比较结构和实际约束表达式。"""
    inspector = inspect(connection)
    normalize = lambda value: re.sub(r"[\s\"`\[\]]", "", str(value)).lower()
    result = {}
    for name in sorted(CORE_TABLES):
        result[name] = {
            "columns": sorted(
                (c["name"], str(c["type"]), c["nullable"], normalize(c["default"]))
                for c in inspector.get_columns(name)
            ),
            "pk": sorted(inspector.get_pk_constraint(name)["constrained_columns"]),
            "fk": sorted(
                (
                    tuple(c["constrained_columns"]),
                    c["referred_table"],
                    tuple(c["referred_columns"]),
                )
                for c in inspector.get_foreign_keys(name)
            ),
            "unique": sorted(
                tuple(c["column_names"]) for c in inspector.get_unique_constraints(name)
            ),
            "checks": sorted(
                normalize(c["sqltext"]) for c in inspector.get_check_constraints(name)
            ),
        }
    return result


def migrate_database(connection: Connection, table_names: set[str]) -> None:
    """已知旧库先备份再标记基线，未知结构拒绝迁移。"""
    from app.migrations.baseline import SIGNATURES

    config = Config()
    config.set_main_option(
        "script_location", str(Path(__file__).with_name("migrations"))
    )
    config.attributes["connection"] = connection
    is_existing = bool(table_names.intersection(CORE_TABLES))
    if (
        is_existing
        and "alembic_version" not in table_names
        and (
            not CORE_TABLES.issubset(table_names)
            or schema_signature(connection) not in SIGNATURES
        )
    ):
        raise RuntimeError("账本结构不属于已知 v0.1/v0.2 基线；请保留数据库并检查版本")
    if "alembic_version" in table_names:
        version = connection.exec_driver_sql(
            "SELECT version_num FROM alembic_version"
        ).scalar()
        if version not in {"0001", "0002"}:
            raise RuntimeError(
                "不支持的账本 Schema 版本；请使用匹配的软件或恢复升级前备份"
            )
    else:
        version = None
    if is_existing and version != "0002":
        # BEGIN IMMEDIATE 已阻止写入；独立只读连接可得到迁移前的一致快照。
        from app.backup import create_backup

        database_path = Path(connection.engine.url.database)
        create_backup(
            database_path,
            database_path.parent / "migration-backups",
            prefix="pre-import",
        )
    if is_existing and version is None:
        command.stamp(config, "0001")
    command.upgrade(config, "head")
