"""PocketTally 单所有者认证、会话和限流服务。"""

from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from urllib.parse import urlsplit

from fastapi import Request, Response
from pwdlib import PasswordHash
from pwdlib.exceptions import PwdlibError
from pwdlib.hashers.argon2 import Argon2Hasher
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.api.errors import ApiError
from app.auth_models import AuthSession, LoginThrottle, Owner
from app.config import Settings

SESSION_COOKIE = "__Host-pockettally_session"
DEV_SESSION_COOKIE = "pockettally_dev_session"
SESSION_IDLE = timedelta(minutes=30)
SESSION_ABSOLUTE = timedelta(hours=12)
THROTTLE_WINDOW = timedelta(minutes=15)
MAX_SESSIONS = 5
PASSWORD_HASH = PasswordHash((Argon2Hasher(memory_cost=65536, time_cost=3, parallelism=1),))
_DUMMY_HASH = PASSWORD_HASH.hash("PocketTally dummy password that is never valid")


@dataclass(frozen=True, slots=True)
class AuthenticatedSession:
    """当前请求已验证的所有者和会话。"""

    owner: Owner
    session: AuthSession


def utc_now() -> datetime:
    """返回数据库使用的 UTC naive datetime。"""

    return datetime.now(UTC).replace(tzinfo=None)


def cookie_name(settings: Settings) -> str:
    """返回按运行模式隔离的会话 Cookie 名称。"""

    return SESSION_COOKIE if settings.environment == "production" else DEV_SESSION_COOKIE


def normalize_username(username: str) -> str:
    """规范化固定所有者用户名。"""

    return username.lower()


def validate_username(username: str) -> str:
    """验证并规范化用户名。"""

    normalized = normalize_username(username)
    if not 3 <= len(normalized) <= 64 or any(
        character not in "abcdefghijklmnopqrstuvwxyz0123456789._-"
        for character in normalized
    ):
        raise ApiError(422, "invalid_username", "用户名必须为 3–64 位字母、数字、点、下划线或连字符")
    return normalized


def validate_password(password: str, *, username: str | None = None) -> None:
    """执行不依赖字符组合的长密码策略。"""

    if not 15 <= len(password) <= 128:
        raise ApiError(422, "invalid_password", "密码长度必须为 15–128 个字符")
    weak_values = {"pockettally", "password", "password123", "123456789012345"}
    if password.casefold() in weak_values or username and password.casefold() == username.casefold():
        raise ApiError(422, "weak_password", "请使用更长且不易猜测的密码")


def client_ip(request: Request) -> str:
    """读取由可信入口计算的客户端地址。"""

    if getattr(request.state, "client_ip", None):
        return request.state.client_ip
    return request.client.host if request.client else "unknown"


def _token_digest(token: str) -> str:
    return hashlib.sha256(token.encode("ascii")).hexdigest()


def _origin(request: Request) -> str | None:
    origin = request.headers.get("origin")
    if origin:
        return origin.rstrip("/")
    referer = request.headers.get("referer")
    if referer:
        parsed = urlsplit(referer)
        if parsed.scheme and parsed.netloc:
            return f"{parsed.scheme}://{parsed.netloc}".rstrip("/")
    return None


def validate_write_request(request: Request, settings: Settings) -> None:
    """验证危险 HTTP 方法的同源和自定义 Header 防护。"""

    expected = settings.public_origin.rstrip("/") if settings.public_origin else f"{request.url.scheme}://{request.headers.get('host', '')}".rstrip("/")
    origin = _origin(request)
    if not origin or origin != expected:
        raise ApiError(403, "request_origin_rejected", "请求来源未通过安全校验")
    if request.headers.get("sec-fetch-site") == "cross-site":
        raise ApiError(403, "request_origin_rejected", "请求来源未通过安全校验")
    if request.headers.get("x-pockettally-csrf") != "1":
        raise ApiError(403, "csrf_rejected", "请求未通过安全校验")
    content_type = request.headers.get("content-type", "")
    if request.method in {"POST", "PUT", "PATCH"} and content_type and not content_type.startswith("application/json"):
        raise ApiError(415, "unsupported_content_type", "认证请求必须使用 JSON")


def _throttle_key(ip: str) -> str:
    return hashlib.sha256(ip.encode("utf-8", "replace")).hexdigest()


def _check_throttle(session: Session, ip: str, now: datetime) -> int | None:
    record = session.scalars(select(LoginThrottle).where(LoginThrottle.client_ip == _throttle_key(ip))).first()
    if record is None:
        return None
    if now - record.window_started_at >= THROTTLE_WINDOW:
        session.delete(record)
        session.flush()
        return None
    if record.blocked_until and record.blocked_until > now:
        return max(1, int((record.blocked_until - now).total_seconds()))
    return None


def _record_failure(session: Session, ip: str, now: datetime) -> None:
    key = _throttle_key(ip)
    record = session.scalars(select(LoginThrottle).where(LoginThrottle.client_ip == key)).first()
    if record is None or now - record.window_started_at >= THROTTLE_WINDOW:
        record = LoginThrottle(client_ip=key, failures=0, window_started_at=now, updated_at=now)
        session.add(record)
    record.failures += 1
    record.updated_at = now
    if record.failures >= 5:
        delay = min(15 * 60, 30 * (2 ** min(record.failures - 5, 5)))
        record.blocked_until = now + timedelta(seconds=delay)
    session.flush()


def _clear_failures(session: Session, ip: str) -> None:
    session.execute(delete(LoginThrottle).where(LoginThrottle.client_ip == _throttle_key(ip)))


def _purge_expired(session: Session, now: datetime) -> None:
    session.execute(delete(AuthSession).where(AuthSession.absolute_expires_at <= now))


def create_session(session: Session, owner: Owner, request: Request, settings: Settings) -> tuple[AuthSession, str]:
    """创建轮换后的服务端会话并执行并发上限。"""

    now = utc_now()
    _purge_expired(session, now)
    token = secrets.token_urlsafe(32)
    row = AuthSession(
        id=secrets.token_hex(16),
        token_digest=_token_digest(token),
        created_at=now,
        last_seen_at=now,
        absolute_expires_at=now + SESSION_ABSOLUTE,
        client_ip=client_ip(request),
        user_agent=request.headers.get("user-agent", "")[:512],
    )
    session.add(row)
    session.flush()
    sessions = session.scalars(select(AuthSession).order_by(AuthSession.created_at.desc())).all()
    for stale in sessions[MAX_SESSIONS:]:
        session.delete(stale)
    return row, token


def set_session_cookie(response: Response, token: str, settings: Settings) -> None:
    """在响应中设置生产或开发会话 Cookie。"""

    response.set_cookie(
        cookie_name(settings),
        token,
        secure=settings.environment == "production",
        httponly=True,
        samesite="strict",
        path="/",
    )


def clear_session_cookie(response: Response, settings: Settings) -> None:
    """清除当前会话 Cookie。"""

    response.delete_cookie(cookie_name(settings), path="/")


def authenticate_request(session: Session, request: Request, settings: Settings) -> AuthenticatedSession:
    """验证当前请求 Cookie 并更新活动时间。"""

    token = request.cookies.get(cookie_name(settings))
    if not token:
        raise ApiError(401, "auth_required", "请先登录")
    now = utc_now()
    row = session.scalars(select(AuthSession).where(AuthSession.token_digest == _token_digest(token))).first()
    owner = session.scalars(select(Owner).limit(1)).first()
    if (
        row is None
        or owner is None
        or row.absolute_expires_at <= now
        or now - row.last_seen_at > SESSION_IDLE
    ):
        if row is not None:
            session.delete(row)
        raise ApiError(401, "auth_required", "请先登录")
    if now - row.last_seen_at >= timedelta(minutes=5):
        row.last_seen_at = now
        session.flush()
    request.state.authenticated_session = row
    return AuthenticatedSession(owner=owner, session=row)


def login(session: Session, request: Request, settings: Settings, username: str, password: str) -> tuple[Owner, AuthSession, str]:
    """验证凭据并创建新会话。"""

    now = utc_now()
    ip = client_ip(request)
    retry_after = _check_throttle(session, ip, now)
    if retry_after:
        raise ApiError(
            429,
            "login_throttled",
            "登录尝试过于频繁，请稍后重试",
            details={"retryAfter": retry_after},
            headers={"Retry-After": str(retry_after)},
        )
    normalized = normalize_username(username)
    owner = session.scalars(select(Owner).where(Owner.username == normalized)).first()
    hash_value = owner.password_hash if owner else _DUMMY_HASH
    try:
        valid, updated_hash = PASSWORD_HASH.verify_and_update(password, hash_value)
    except PwdlibError:
        valid, updated_hash = False, None
    if not owner or not valid:
        _record_failure(session, ip, now)
        raise ApiError(401, "invalid_credentials", "用户名或密码错误")
    if updated_hash:
        owner.password_hash = updated_hash
    _clear_failures(session, ip)
    row, token = create_session(session, owner, request, settings)
    return owner, row, token
