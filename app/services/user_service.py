"""游客会话服务：昵称校验、会话签发与鉴权。仅存昵称，不落任何个人数据。"""
import re
import secrets
from datetime import datetime, timedelta
from typing import Optional, Tuple

from app.config import SESSION_TTL_SECONDS, USERNAME_MAX_LEN
from app.models import db
from app.models.schemas import ErrorCode

_PHONE_RE = re.compile(r"^(\+?86)?1[3-9]\d{9}$")
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def validate_username(username: str) -> Tuple[Optional[int], Optional[str]]:
    """返回 (错误码或 None, 错误消息或 None)。"""
    if username is None or username.strip() == "":
        return ErrorCode.USERNAME_EMPTY, "用户名不能为空"
    if len(username) > USERNAME_MAX_LEN:
        return ErrorCode.USERNAME_TOO_LONG, f"用户名不能超过{USERNAME_MAX_LEN}个字符"
    if _PHONE_RE.match(username):
        return ErrorCode.LOGIN_MODE_FORBIDDEN, "仅支持游客模式，不允许手机号登录"
    if _EMAIL_RE.match(username):
        return ErrorCode.LOGIN_MODE_FORBIDDEN, "仅支持游客模式，不允许邮箱登录"
    return None, None


def enter(username: str, gender: str = "保密") -> str:
    """签发会话令牌并写入 sessions 表（性别仅作会话临时标识，用于队伍性别约束）。"""
    token = "sess_" + secrets.token_hex(16)
    expires_at = (datetime.now() + timedelta(seconds=SESSION_TTL_SECONDS)).isoformat()
    conn = db.get_conn()
    try:
        conn.execute(
            "INSERT INTO sessions (token, username, gender, expires_at) VALUES (?, ?, ?, ?)",
            (token, username, gender, expires_at),
        )
        conn.commit()
    finally:
        conn.close()
    return token


def authenticate(token: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
    """校验令牌，有效则返回 (用户名, 性别)，否则 (None, None)，并清理过期会话。"""
    if not token:
        return None, None
    conn = db.get_conn()
    try:
        row = conn.execute(
            "SELECT username, gender, expires_at FROM sessions WHERE token = ?", (token,)
        ).fetchone()
        if row is None:
            return None, None
        try:
            expires = datetime.fromisoformat(row["expires_at"])
        except ValueError:
            expires = datetime.min
        if expires <= datetime.now():
            conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
            conn.commit()
            return None, None
        return row["username"], row["gender"]
    finally:
        conn.close()