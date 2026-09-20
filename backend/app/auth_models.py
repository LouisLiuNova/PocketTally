"""独立鉴权 SQLite 数据库的 SQLAlchemy 模型。"""

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class AuthBase(DeclarativeBase):
    """鉴权库专用元数据，避免与账本 SQLModel 元数据混用。"""


class Owner(AuthBase):
    """单一账本所有者。"""

    __tablename__ = "owner"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    password_changed_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class AuthSession(AuthBase):
    """服务端不透明会话。"""

    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    token_digest: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    absolute_expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    client_ip: Mapped[str] = mapped_column(String(255), nullable=False)
    user_agent: Mapped[str] = mapped_column(String(512), nullable=False)


class LoginThrottle(AuthBase):
    """按可信客户端地址持久化登录失败退避状态。"""

    __tablename__ = "login_throttle"
    __table_args__ = (UniqueConstraint("client_ip", name="uq_login_throttle_client_ip"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    client_ip: Mapped[str] = mapped_column(String(255), nullable=False)
    failures: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    window_started_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    blocked_until: Mapped[datetime | None] = mapped_column(DateTime)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
