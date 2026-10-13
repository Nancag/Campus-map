"""拼车队伍处理器：发布 / 搜索 / 详情 / 加入 / 退出 / 状态流转。"""
from types import SimpleNamespace

from app.api.deps import as_float, as_int
from app.models.domain import TripStatus
from app.models.schemas import ErrorCode, err, ok
from app.services import trip_service


def _trip_req(body):
    return SimpleNamespace(
        teamName=body.get("teamName"),
        origin=(body.get("origin") or ""),
        destination=(body.get("destination") or ""),
        departAt=(body.get("departAt") or ""),
        seats=as_int(body.get("seats"), default=0),
        fee=as_float(body.get("fee")),
        originLat=body.get("originLat"),
        originLng=body.get("originLng"),
        destinationLat=body.get("destinationLat"),
        destinationLng=body.get("destinationLng"),
        gender=(body.get("gender") or ""),
        remark=body.get("remark"),
    )


def create_trip(h, body, path_params):
    _token, username, _gender = h.get_session()
    code, msg, data = trip_service.create_trip(username, _trip_req(body), _gender)
    return ok(data) if code == ErrorCode.OK else err(code, msg)


def list_trips(h, body, path_params):
    h.get_session()
    origin = h.q("origin") or None
    destination = h.q("destination") or None
    depart_from = h.q("departFrom") or None
    depart_to = h.q("departTo") or None
    page = max(1, h.int_q("page", 1))
    size = min(100, max(1, h.int_q("size", 20)))
    items, total = trip_service.list_trips(origin, destination, depart_from, depart_to, page, size)
    return ok({"items": items, "total": total})


def get_trip(h, body, path_params):
    h.get_session()
    trip = trip_service.get_trip(path_params["id"])
    return ok(trip) if trip else err(ErrorCode.NOT_FOUND, "队伍不存在")


def join_trip(h, body, path_params):
    token, username, gender = h.get_session()
    code, msg, data = trip_service.join_trip(username, gender, token, path_params["id"])
    return ok(data) if code == ErrorCode.OK else err(code, msg)


def leave_trip(h, body, path_params):
    token, username, _ = h.get_session()
    code, msg, data = trip_service.leave_trip(username, token, path_params["id"])
    return ok(data) if code == ErrorCode.OK else err(code, msg)


def depart(h, body, path_params):
    _token, username, _ = h.get_session()
    code, msg, data = trip_service.change_status(username, path_params["id"], TripStatus.DEPARTED)
    return ok(data) if code == ErrorCode.OK else err(code, msg)


def complete(h, body, path_params):
    _token, username, _ = h.get_session()
    code, msg, data = trip_service.change_status(username, path_params["id"], TripStatus.COMPLETED)
    return ok(data) if code == ErrorCode.OK else err(code, msg)


def cancel(h, body, path_params):
    _token, username, _ = h.get_session()
    code, msg, data = trip_service.change_status(username, path_params["id"], TripStatus.CANCELED)
    return ok(data) if code == ErrorCode.OK else err(code, msg)

def edit_trip(h, body, path_params):
    _token, username, _ = h.get_session()
    code, msg, data = trip_service.edit_trip(username, path_params["id"], body)
    return ok(data) if code == ErrorCode.OK else err(code, msg)


def kick_member(h, body, path_params):
    _token, username, _ = h.get_session()
    target = body.get("username") or ""
    code, msg, data = trip_service.kick_member(username, path_params["id"], target)
    return ok(data) if code == ErrorCode.OK else err(code, msg)


def dissolve_trip(h, body, path_params):
    _token, username, _ = h.get_session()
    code, msg, data = trip_service.dissolve_trip(username, path_params["id"])
    return ok(data) if code == ErrorCode.OK else err(code, msg)


def list_members(h, body, path_params):
    h.get_session()
    code, msg, data = trip_service.list_members(path_params["id"])
    return ok(data) if code == ErrorCode.OK else err(code, msg)


def my_teams(h, body, path_params):
    _token, username, _ = h.get_session()
    items = trip_service.get_trips_by_leader(username)
    return ok({"items": items, "total": len(items)})