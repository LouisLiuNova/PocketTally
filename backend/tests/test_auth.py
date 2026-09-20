"""Issue #22 单用户鉴权边界测试。"""

from datetime import timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.auth import PASSWORD_HASH, SESSION_IDLE, utc_now
from app.auth_models import AuthSession, Owner
from app.config import Settings
from app.main import create_app

PASSWORD = "correct horse battery staple"
HEADERS = {
    "Origin": "http://testserver",
    "X-PocketTally-CSRF": "1",
    "Content-Type": "application/json",
}


def make_client(tmp_path: Path) -> tuple[TestClient, object]:
    app = create_app(
        Settings(
            environment="test",
            auth_enabled=True,
            database_path=tmp_path / "ledger.sqlite3",
            auth_database_path=tmp_path / "auth.sqlite3",
        )
    )
    client = TestClient(app)
    client.__enter__()
    now = utc_now()
    with Session(app.state.resources.auth_engine) as session, session.begin():
        session.add(
            Owner(
                id=1,
                username="owner",
                password_hash=PASSWORD_HASH.hash(PASSWORD),
                created_at=now,
                password_changed_at=now,
            )
        )
    return client, app


def test_anonymous_cannot_read_ledger(tmp_path: Path) -> None:
    client, _app = make_client(tmp_path)
    try:
        response = client.get("/api/v1/accounts")
        assert response.status_code == 401
        assert "accounts" not in response.text
    finally:
        client.__exit__(None, None, None)


def test_login_cookie_session_and_logout(tmp_path: Path) -> None:
    client, _app = make_client(tmp_path)
    try:
        response = client.post(
            "/api/v1/auth/login",
            json={"username": "owner", "password": PASSWORD},
            headers=HEADERS,
        )
        assert response.status_code == 200
        cookie = response.headers["set-cookie"]
        assert "HttpOnly" in cookie
        assert "SameSite=strict" in cookie
        assert "Secure" not in cookie
        assert client.get("/api/v1/auth/session").status_code == 200
        assert client.get("/api/v1/accounts").status_code == 200
        assert client.post("/api/v1/auth/logout", headers=HEADERS).status_code == 204
        assert client.get("/api/v1/accounts").status_code == 401
    finally:
        client.__exit__(None, None, None)


def test_login_requires_origin_and_csrf_header(tmp_path: Path) -> None:
    client, _app = make_client(tmp_path)
    try:
        response = client.post(
            "/api/v1/auth/login",
            json={"username": "owner", "password": PASSWORD},
            headers={"Origin": "http://testserver"},
        )
        assert response.status_code == 403
    finally:
        client.__exit__(None, None, None)


def test_password_change_revokes_old_session(tmp_path: Path) -> None:
    client, _app = make_client(tmp_path)
    try:
        assert client.post(
            "/api/v1/auth/login",
            json={"username": "owner", "password": PASSWORD},
            headers=HEADERS,
        ).status_code == 200
        response = client.put(
            "/api/v1/auth/password",
            json={"currentPassword": PASSWORD, "newPassword": "another correct horse battery"},
            headers=HEADERS,
        )
        assert response.status_code == 200
        assert client.get("/api/v1/auth/session").status_code == 200
    finally:
        client.__exit__(None, None, None)


def test_idle_session_expires_and_401_clears_cookie(tmp_path: Path) -> None:
    client, app = make_client(tmp_path)
    try:
        assert client.post(
            "/api/v1/auth/login",
            json={"username": "owner", "password": PASSWORD},
            headers=HEADERS,
        ).status_code == 200
        with Session(app.state.resources.auth_engine) as session, session.begin():
            row = session.query(AuthSession).one()
            row.last_seen_at = utc_now() - SESSION_IDLE - timedelta(seconds=1)
        response = client.get("/api/v1/accounts")
        assert response.status_code == 401
        assert "Max-Age=0" in response.headers.get("set-cookie", "")
    finally:
        client.__exit__(None, None, None)


def test_production_requires_https_public_origin(tmp_path: Path) -> None:
    app = create_app(
        Settings(
            environment="production",
            auth_enabled=True,
            database_path=tmp_path / "ledger.sqlite3",
            auth_database_path=tmp_path / "auth.sqlite3",
            public_origin="http://example.test",
        )
    )
    with pytest.raises(RuntimeError, match="HTTPS"), TestClient(app):
        pass
