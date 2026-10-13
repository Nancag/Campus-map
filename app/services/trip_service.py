"""拼车队伍业务服务：发布校验、搜索过滤、加入/退出、状态流转。"""
import threading
from datetime import datetime
from typing import Optional, Tuple

from app.config import (
    CAMPUS_GATE_NAMES,
    GENDER_FEMALE_ONLY,
    GENDER_MALE_ONLY,
    GENDER_NONE,
    MAX_SEATS,
    REMARK_MAX_LEN,
    TEAM_GENDERS,
    TEAM_NAME_MAX_LEN,
)
from app.models.domain import TripStatus, can_transition
from app.models.schemas import ErrorCode
from app.repositories import campus_repo, trip_repo


def _is_gate_name(text: str) -> bool:
    """判断文本是否包含任一校区的校门名称。"""
    if not text:
        return False
    for gate_list in CAMPUS_GATE_NAMES.values():
        for gate_name in gate_list:
            if gate_name in text:
                return True
    return False

# 会话级「已加入队伍集合」（内存态，不落库）：token -> {trip_id}
_joined_lock = threading.Lock()
_joined: dict = {}


def point_in_service_range(lat: Optional[float], lng: Optional[float]) -> bool:
    """判断某坐标是否位于任一支持校区 40km 范围内。"""
    if lat is None or lng is None:
        return True
    try:
        lat, lng = float(lat), float(lng)
    except (TypeError, ValueError):
        return False
    return any(campus.contains(lat, lng) for campus in campus_repo.list_campuses())


def _out_of_range(trip: dict) -> bool:
    for lat_key, lng_key in (("originLat", "originLng"), ("destinationLat", "destinationLng")):
        lat, lng = trip.get(lat_key), trip.get(lng_key)
        if lat is not None and lng is not None and not point_in_service_range(lat, lng):
            return True
    return False


def create_trip(username: str, req, user_gender: str = "保密") -> Tuple[int, Optional[str], Optional[dict]]:
    team_name = (getattr(req, "teamName", None) or "").strip()
    origin = (req.origin or "").strip()
    destination = (req.destination or "").strip()
    depart_at = (req.departAt or "").strip()
    gender = (getattr(req, "gender", None) or GENDER_NONE).strip()
    remark = getattr(req, "remark", None)

    if not team_name:
        return ErrorCode.TEAM_NAME_INVALID, "队名必填", None
    if len(team_name) > TEAM_NAME_MAX_LEN:
        return ErrorCode.TEAM_NAME_INVALID, f"队名不能超过{TEAM_NAME_MAX_LEN}字", None
    if not origin or not destination or not depart_at:
        return ErrorCode.TRIP_FIELD_MISSING, "出发地、目的地、出发时间必填", None
    if req.seats < 2:
        return ErrorCode.SEATS_INVALID, "最大人数须不小于 2", None
    if req.seats > MAX_SEATS:
        return ErrorCode.SEATS_OVER_LIMIT, f"最大人数不得超过{MAX_SEATS}人", None
    if req.fee is not None and req.fee < 0:
        return ErrorCode.TRIP_FIELD_MISSING, "费用须为非负数值", None
    if gender not in TEAM_GENDERS:
        return ErrorCode.TRIP_FIELD_MISSING, "性别要求非法", None
    if remark and len(remark) > REMARK_MAX_LEN:
        return ErrorCode.TRIP_FIELD_MISSING, f"备注不能超过{REMARK_MAX_LEN}字", None

    try:
        depart = datetime.fromisoformat(depart_at)
    except ValueError:
        return ErrorCode.TRIP_FIELD_MISSING, "出发时间格式非法", None
    if depart <= datetime.now():
        return ErrorCode.TRIP_FIELD_MISSING, "出发时间须晚于当前时间", None

    if not point_in_service_range(req.originLat, req.originLng):
        return ErrorCode.OUT_OF_RANGE, "出发地不在服务范围内（校区周边40km）", None
    if not point_in_service_range(req.destinationLat, req.destinationLng):
        return ErrorCode.OUT_OF_RANGE, "目的地不在服务范围内（校区周边40km）", None

    if not _is_gate_name(origin) and not _is_gate_name(destination):
        return ErrorCode.GATE_REQUIRED, "出发点或目的地至少有一个必须是学校校门", None

    import uuid

    trip = {
        "tripId": "t_" + uuid.uuid4().hex[:12],
        "teamName": team_name,
        "origin": origin,
        "destination": destination,
        "originLat": req.originLat,
        "originLng": req.originLng,
        "destinationLat": req.destinationLat,
        "destinationLng": req.destinationLng,
        "departAt": depart_at,
        "maxSeats": req.seats,
        "currentSeats": 1,
        "fee": req.fee,
        "leaderName": username,
        "status": TripStatus.OPEN.value,
        "gender": gender,
        "remark": remark,
        "createdAt": datetime.now().isoformat(),
    }
    trip_repo.create(trip)
    trip_repo.add_member(trip["tripId"], username, user_gender)
    return ErrorCode.OK, "ok", {"tripId": trip["tripId"], "status": trip["status"]}


def list_trips(origin, destination, depart_from, depart_to, page, size):
    items, total = trip_repo.search(origin, destination, depart_from, depart_to, page, size)
    items = [t for t in items if not _out_of_range(t)]
    return items, total


def get_trip(trip_id: str) -> Optional[dict]:
    return trip_repo.find_by_id(trip_id)


def join_trip(username: str, gender: str, token: str, trip_id: str) -> Tuple[int, str, Optional[dict]]:
    trip = trip_repo.find_by_id(trip_id)
    if trip is None:
        return ErrorCode.NOT_FOUND, "队伍不存在", None
    if trip["leaderName"] == username:
        return ErrorCode.JOIN_OWN_TRIP, "不能加入自己的队伍", None
    if trip["status"] not in (TripStatus.OPEN.value, TripStatus.FULL.value):
        return ErrorCode.FORBIDDEN, "队伍已结束，无法加入", None

    team_gender = (trip.get("gender") or GENDER_NONE).strip()
    if team_gender == GENDER_FEMALE_ONLY and gender != "女":
        return ErrorCode.GENDER_MISMATCH, "该队伍仅限女生加入", None
    if team_gender == GENDER_MALE_ONLY and gender != "男":
        return ErrorCode.GENDER_MISMATCH, "该队伍仅限男生加入", None

    if trip_repo.is_member(trip_id, username):
        return ErrorCode.DUPLICATE_JOIN, "已加入该队伍，请勿重复加入", None
    if trip["currentSeats"] >= trip["maxSeats"]:
        return ErrorCode.TRIP_FULL, "队伍已满员", None
    if not trip_repo.atomic_join(trip_id):
        return ErrorCode.SEAT_TAKEN, "座位已被抢占", None
    trip_repo.add_member(trip_id, username, gender)

    return ErrorCode.OK, "ok", {"tripId": trip_id, "currentSeats": trip["currentSeats"] + 1}


def leave_trip(username: str, token: str, trip_id: str) -> Tuple[int, str, Optional[dict]]:
    trip = trip_repo.find_by_id(trip_id)
    if trip is None:
        return ErrorCode.NOT_FOUND, "队伍不存在", None
    if trip["leaderName"] == username:
        return ErrorCode.FORBIDDEN, "队长无法退出队伍，可取消队伍", None
    if trip["status"] not in (TripStatus.OPEN.value, TripStatus.FULL.value):
        return ErrorCode.FORBIDDEN, "队伍已结束，无法退出", None

    if not trip_repo.is_member(trip_id, username):
        return ErrorCode.FORBIDDEN, "您未加入该队伍", None
    if not trip_repo.atomic_leave(trip_id):
        return ErrorCode.SEAT_TAKEN, "退出失败，请重试", None
    trip_repo.remove_member(trip_id, username)

    return ErrorCode.OK, "ok", {"tripId": trip_id, "currentSeats": max(trip["currentSeats"] - 1, 0)}


def change_status(username: str, trip_id: str, target: TripStatus) -> Tuple[int, str, Optional[dict]]:
    trip = trip_repo.find_by_id(trip_id)
    if trip is None:
        return ErrorCode.NOT_FOUND, "队伍不存在", None
    if trip["leaderName"] != username:
        return ErrorCode.FORBIDDEN, "仅队长可执行该操作", None

    current = TripStatus(trip["status"])
    if not can_transition(current, target):
        return ErrorCode.FORBIDDEN, f"非法状态流转：{current.value} 不可变为 {target.value}", None

    if not trip_repo.update_status(trip_id, target.value):
        return ErrorCode.NOT_FOUND, "队伍不存在", None
    return ErrorCode.OK, "ok", {"tripId": trip_id, "status": target.value}

def edit_trip(username: str, trip_id: str, fields: dict) -> Tuple[int, str, Optional[dict]]:
    trip = trip_repo.find_by_id(trip_id)
    if trip is None:
        return ErrorCode.NOT_FOUND, "队伍不存在", None
    if trip["leaderName"] != username:
        return ErrorCode.NOT_LEADER, "仅队长可编辑队伍", None
    if trip["status"] in (TripStatus.COMPLETED.value, TripStatus.CANCELED.value):
        return ErrorCode.FORBIDDEN, "队伍已结束，无法编辑", None

    if "teamName" in fields:
        tn = (fields["teamName"] or "").strip()
        if not tn:
            return ErrorCode.TEAM_NAME_INVALID, "队名不能为空", None
        if len(tn) > TEAM_NAME_MAX_LEN:
            return ErrorCode.TEAM_NAME_INVALID, f"队名不能超过{TEAM_NAME_MAX_LEN}字", None
        fields["teamName"] = tn

    if "maxSeats" in fields:
        ms = int(fields["maxSeats"])
        if ms < 2:
            return ErrorCode.SEATS_INVALID, "人数须不小于 2", None
        if ms > MAX_SEATS:
            return ErrorCode.SEATS_OVER_LIMIT, f"最大人数不得超过{MAX_SEATS}人", None
        if ms < trip["currentSeats"]:
            return ErrorCode.SEATS_OVER_LIMIT, "人数上限不能小于当前队伍人数", None
        fields["maxSeats"] = ms

    if "gender" in fields and fields["gender"] not in TEAM_GENDERS:
        return ErrorCode.TRIP_FIELD_MISSING, "性别要求非法", None

    if "remark" in fields and fields["remark"] and len(fields["remark"]) > REMARK_MAX_LEN:
        return ErrorCode.TRIP_FIELD_MISSING, f"备注不能超过{REMARK_MAX_LEN}字", None

    trip_repo.update_trip(trip_id, fields)
    updated = trip_repo.find_by_id(trip_id)
    return ErrorCode.OK, "ok", updated


def kick_member(username: str, trip_id: str, target_username: str) -> Tuple[int, str, Optional[dict]]:
    trip = trip_repo.find_by_id(trip_id)
    if trip is None:
        return ErrorCode.NOT_FOUND, "队伍不存在", None
    if trip["leaderName"] != username:
        return ErrorCode.NOT_LEADER, "仅队长可踢出成员", None
    if target_username == username:
        return ErrorCode.FORBIDDEN, "不能踢出自己", None
    if not trip_repo.is_member(trip_id, target_username):
        return ErrorCode.MEMBER_NOT_FOUND, "该用户不在队伍中", None

    trip_repo.remove_member(trip_id, target_username)
    trip_repo.atomic_leave(trip_id)
    return ErrorCode.OK, "ok", {"tripId": trip_id, "removed": target_username}


def dissolve_trip(username: str, trip_id: str) -> Tuple[int, str, Optional[dict]]:
    trip = trip_repo.find_by_id(trip_id)
    if trip is None:
        return ErrorCode.NOT_FOUND, "队伍不存在", None
    if trip["leaderName"] != username:
        return ErrorCode.NOT_LEADER, "仅队长可解散队伍", None

    trip_repo.clear_members(trip_id)
    trip_repo.update_status(trip_id, TripStatus.CANCELED.value)
    return ErrorCode.OK, "ok", {"tripId": trip_id, "status": "已取消"}


def list_members(trip_id: str) -> Tuple[int, str, Optional[dict]]:
    trip = trip_repo.find_by_id(trip_id)
    if trip is None:
        return ErrorCode.NOT_FOUND, "队伍不存在", None
    members = trip_repo.list_members(trip_id)
    if not any(m["username"] == trip["leaderName"] for m in members):
        members.insert(0, {"username": trip["leaderName"], "gender": "保密", "joinedAt": trip["createdAt"]})
    return ErrorCode.OK, "ok", {"leader": trip["leaderName"], "members": members}


def get_trips_by_leader(username: str) -> list:
    return trip_repo.get_trips_by_leader(username)