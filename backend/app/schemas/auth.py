"""认证 HTTP 契约。"""

from datetime import UTC, datetime
from typing import Annotated

from pydantic import ConfigDict, Field, StringConstraints, field_serializer

from app.schemas.base import ContractModel

Username = Annotated[str, StringConstraints(min_length=3, max_length=64)]
Password = Annotated[str, StringConstraints(min_length=1, max_length=128)]


class LoginRequest(ContractModel):
    model_config = ConfigDict(str_strip_whitespace=False)

    username: Username
    password: Password


class PasswordChangeRequest(ContractModel):
    model_config = ConfigDict(str_strip_whitespace=False)

    current_password: Password
    new_password: Password


class SessionRead(ContractModel):
    id: str
    username: str
    current: bool
    created_at: datetime
    last_seen_at: datetime
    absolute_expires_at: datetime

    @classmethod
    def from_values(cls, *, session, username: str, current: bool) -> SessionRead:
        return cls(
            id=session.id,
            username=username,
            current=current,
            created_at=session.created_at,
            last_seen_at=session.last_seen_at,
            absolute_expires_at=session.absolute_expires_at,
        )

    @field_serializer("last_seen_at", "absolute_expires_at")
    def serialize_auth_datetime(self, value: object) -> object:
        if not isinstance(value, datetime):
            return value
        aware = value if value.tzinfo is not None else value.replace(tzinfo=UTC)
        return aware.astimezone(UTC).isoformat().replace("+00:00", "Z")


class SessionList(ContractModel):
    sessions: list[SessionRead] = Field(default_factory=list)
