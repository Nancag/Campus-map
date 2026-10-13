"""业务错误码、统一响应结构与异常类型（无第三方依赖）。"""


class ErrorCode:
    OK = 0
    USERNAME_EMPTY = 1001
    USERNAME_TOO_LONG = 1002
    LOGIN_MODE_FORBIDDEN = 1003
    TRIP_FIELD_MISSING = 2001
    OUT_OF_RANGE = 2002
    SEATS_INVALID = 2003
    SEATS_OVER_LIMIT = 2004
    GATE_REQUIRED = 2005
    TEAM_NAME_INVALID = 2006
    TRIP_FULL = 3001
    JOIN_OWN_TRIP = 3002
    DUPLICATE_JOIN = 3003
    SEAT_TAKEN = 3004
    GENDER_MISMATCH = 3005
    NOT_LEADER = 3006
    MEMBER_NOT_FOUND = 3007
    POST_TITLE_INVALID = 5001
    POST_CONTENT_INVALID = 5002
    UNAUTHORIZED = 9001
    NOT_FOUND = 9002
    FORBIDDEN = 9003


class AppError(Exception):
    """业务/HTTP 错误：携带状态码、业务错误码与提示信息。"""

    def __init__(self, status: int, code: int, message: str):
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message


def ok(data=None, message: str = "ok") -> dict:
    return {"code": ErrorCode.OK, "message": message, "data": data}


def err(code: int, message: str, data=None) -> dict:
    return {"code": code, "message": message, "data": data}