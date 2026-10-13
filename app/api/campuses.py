"""校区信息处理器：GET /api/campuses（含校区入口 gates）。"""
from app.models.schemas import ok
from app.repositories import campus_repo


def list_campuses(h, body, path_params):
    h.get_session()
    items = []
    for c in campus_repo.list_campuses():
        d = c.to_dict()
        d["gates"] = campus_repo.get_gates(c.name)
        items.append(d)
    return ok({"items": items})