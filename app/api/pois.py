"""POI 地点处理器：GET /api/pois"""
from app.models.schemas import ok
from app.repositories import campus_repo


def list_pois(h, body, path_params):
    h.get_session()
    return ok({"items": campus_repo.list_pois()})