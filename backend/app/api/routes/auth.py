"""单所有者认证路由。"""

from fastapi import APIRouter, Request, Response, status
from pwdlib.exceptions import PwdlibError
from sqlalchemy import delete, select

from app.api.errors import ApiError
from app.auth import (
    PASSWORD_HASH,
    clear_session_cookie,
    create_session,
    login,
    set_session_cookie,
    utc_now,
    validate_password,
    validate_username,
    validate_write_request,
)
from app.auth_models import AuthSession
from app.dependencies import AuthDep, AuthSessionDep, SettingsDep
from app.schemas.auth import (
    LoginRequest,
    PasswordChangeRequest,
    SessionList,
    SessionRead,
)

router = APIRouter(prefix="/auth", tags=["auth"])


def require_auth_enabled(auth_session: AuthSessionDep) -> None:
    if auth_session is None:
        raise ApiError(503, "auth_unavailable", "鉴权服务尚未初始化")


@router.post("/login", response_model=SessionRead, operation_id="login")
def login_route(
    payload: LoginRequest,
    request: Request,
    response: Response,
    settings: SettingsDep,
    auth_session: AuthSessionDep,
) -> SessionRead:
    """验证所有者凭据并轮换会话。"""

    require_auth_enabled(auth_session)
    validate_write_request(request, settings)
    username = validate_username(payload.username)
    owner, session, token = login(auth_session, request, settings, username, payload.password)
    set_session_cookie(response, token, settings)
    return SessionRead.from_values(session=session, username=owner.username, current=True)


@router.get("/session", response_model=SessionRead, operation_id="getAuthSession")
def get_auth_session_route(
    request: Request,
    settings: SettingsDep,
    auth: AuthDep,
) -> SessionRead:
    """返回当前会话，匿名请求统一失败。"""

    if auth is None:
        raise ApiError(401, "auth_required", "请先登录")
    return SessionRead.from_values(session=auth.session, username=auth.owner.username, current=True)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, operation_id="logout")
def logout_route(
    request: Request,
    response: Response,
    settings: SettingsDep,
    auth_session: AuthSessionDep,
    auth: AuthDep,
) -> None:
    """删除当前会话。"""

    if auth is None:
        raise ApiError(401, "auth_required", "请先登录")
    validate_write_request(request, settings)
    auth_session.delete(auth.session)
    clear_session_cookie(response, settings)


@router.get("/sessions", response_model=SessionList, operation_id="listAuthSessions")
def list_sessions_route(auth_session: AuthSessionDep, auth: AuthDep) -> SessionList:
    """返回当前所有者的非敏感会话摘要。"""

    if auth is None:
        raise ApiError(401, "auth_required", "请先登录")
    rows = auth_session.scalars(select(AuthSession).order_by(AuthSession.created_at.desc())).all()
    return SessionList(
        sessions=[
            SessionRead.from_values(session=row, username=auth.owner.username, current=row.id == auth.session.id)
            for row in rows
        ]
    )


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT, operation_id="revokeAuthSession")
def revoke_session_route(
    session_id: str,
    request: Request,
    response: Response,
    settings: SettingsDep,
    auth_session: AuthSessionDep,
    auth: AuthDep,
) -> None:
    """撤销指定会话。"""

    if auth is None:
        raise ApiError(401, "auth_required", "请先登录")
    validate_write_request(request, settings)
    row = auth_session.get(AuthSession, session_id)
    if row is None:
        return
    auth_session.delete(row)
    if row.id == auth.session.id:
        clear_session_cookie(response, settings)


@router.delete("/sessions", status_code=status.HTTP_204_NO_CONTENT, operation_id="revokeAllAuthSessions")
def revoke_all_sessions_route(
    request: Request,
    response: Response,
    settings: SettingsDep,
    auth_session: AuthSessionDep,
    auth: AuthDep,
) -> None:
    """撤销所有会话。"""

    if auth is None:
        raise ApiError(401, "auth_required", "请先登录")
    validate_write_request(request, settings)
    auth_session.execute(delete(AuthSession))
    clear_session_cookie(response, settings)


@router.put("/password", response_model=SessionRead, operation_id="changePassword")
def change_password_route(
    payload: PasswordChangeRequest,
    request: Request,
    response: Response,
    settings: SettingsDep,
    auth_session: AuthSessionDep,
    auth: AuthDep,
) -> SessionRead:
    """重新验证当前密码、更新密码并轮换全部会话。"""

    if auth is None:
        raise ApiError(401, "auth_required", "请先登录")
    validate_write_request(request, settings)
    try:
        valid = PASSWORD_HASH.verify(payload.current_password, auth.owner.password_hash)
    except PwdlibError:
        valid = False
    if not valid:
        raise ApiError(401, "invalid_credentials", "当前密码错误")
    validate_password(payload.new_password, username=auth.owner.username)
    auth.owner.password_hash = PASSWORD_HASH.hash(payload.new_password)
    auth.owner.password_changed_at = utc_now()
    auth_session.execute(delete(AuthSession))
    auth_session.flush()
    row, token = create_session(auth_session, auth.owner, request, settings)
    set_session_cookie(response, token, settings)
    return SessionRead.from_values(session=row, username=auth.owner.username, current=True)


__all__ = ("router",)
