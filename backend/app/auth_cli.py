"""鉴权库初始化和应急恢复命令。"""

from __future__ import annotations

import argparse
import getpass
import sys

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.api.errors import ApiError
from app.auth import PASSWORD_HASH, utc_now, validate_password, validate_username
from app.auth_database import (
    create_auth_database_engine,
    database_process_lock,
    initialize_auth_database,
    resolve_auth_database_path,
)
from app.auth_models import AuthSession, Owner
from app.config import get_settings


def _password() -> str:
    password = getpass.getpass("密码：")
    confirmation = getpass.getpass("确认密码：")
    if password != confirmation:
        raise SystemExit("两次输入的密码不一致")
    return password


def _database():
    settings = get_settings()
    path = resolve_auth_database_path(settings.database_path, settings.auth_database_path)
    return path, create_auth_database_engine(path)


def init_owner(username: str | None) -> None:
    path, engine = _database()
    try:
        with database_process_lock(path):
            initialize_auth_database(engine)
            with Session(engine) as session, session.begin():
                if session.scalars(select(Owner).limit(1)).first() is not None:
                    raise SystemExit("所有者已初始化；如需恢复请使用 reset-password")
                name = validate_username(username or input("用户名：").strip())
                password = _password()
                validate_password(password, username=name)
                now = utc_now()
                session.add(Owner(
                    id=1,
                    username=name,
                    password_hash=PASSWORD_HASH.hash(password),
                    created_at=now,
                    password_changed_at=now,
                ))
    finally:
        engine.dispose()
    print(f"已初始化所有者：{name}")


def reset_password() -> None:
    path, engine = _database()
    try:
        with database_process_lock(path):
            initialize_auth_database(engine)
            with Session(engine) as session, session.begin():
                owner = session.scalars(select(Owner).limit(1)).first()
                if owner is None:
                    raise SystemExit("尚未初始化所有者，请先使用 init")
                password = _password()
                validate_password(password, username=owner.username)
                owner.password_hash = PASSWORD_HASH.hash(password)
                owner.password_changed_at = utc_now()
                session.execute(delete(AuthSession))
                name = owner.username
    finally:
        engine.dispose()
    print(f"已重设密码并撤销全部会话：{name}")


def revoke_sessions() -> None:
    path, engine = _database()
    try:
        with database_process_lock(path):
            initialize_auth_database(engine)
            with Session(engine) as session, session.begin():
                deleted = session.query(AuthSession).delete()
    finally:
        engine.dispose()
    print(f"已撤销会话：{deleted}")


def status() -> None:
    path, engine = _database()
    try:
        with database_process_lock(path):
            initialize_auth_database(engine)
            with Session(engine) as session:
                owner = session.scalars(select(Owner).limit(1)).first()
                count = session.query(AuthSession).count()
    finally:
        engine.dispose()
    print(f"已初始化：{'是' if owner else '否'}")
    print(f"有效会话：{count}")


def main() -> None:
    parser = argparse.ArgumentParser(description="PocketTally 鉴权管理")
    subparsers = parser.add_subparsers(dest="command", required=True)
    init_parser = subparsers.add_parser("init", help="初始化所有者")
    init_parser.add_argument("--username")
    subparsers.add_parser("reset-password", help="重设密码并撤销全部会话")
    subparsers.add_parser("revoke-sessions", help="撤销全部会话")
    subparsers.add_parser("status", help="查看最小鉴权状态")
    arguments = parser.parse_args()
    try:
        if arguments.command == "init":
            init_owner(arguments.username)
        elif arguments.command == "reset-password":
            reset_password()
        elif arguments.command == "revoke-sessions":
            revoke_sessions()
        else:
            status()
    except (ApiError, ValueError, RuntimeError) as error:
        print(str(error), file=sys.stderr)
        raise SystemExit(1) from error


if __name__ == "__main__":
    main()
