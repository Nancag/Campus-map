"""游客进入处理器：POST /api/guest/enter"""
from app.config import GENDER_NONE, TEAM_GENDERS
from app.models.schemas import ErrorCode, err, ok
from app.services import user_service

_VALID_GENDERS = {"男", "女", "保密"}


def enter(h, body, path_params):
    username = (body.get("username") or "").strip()
    gender = (body.get("gender") or "保密").strip()
    code, msg = user_service.validate_username(username)
    if code is not None:
        return err(code, msg)
    if gender not in _VALID_GENDERS:
        return err(ErrorCode.TRIP_FIELD_MISSING, "性别须为 男/女/保密")
    token = user_service.enter(username, gender)
    return ok({"token": token, "username": username, "gender": gender})