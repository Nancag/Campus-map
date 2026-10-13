"""校区、入口与 POI 地点数据读取：校区/入口来自 config，POI 来自本地 OSM 缓存。"""
import json
from typing import List

from app.config import CAMPUS_GATES, OSM_POIS_PATH, SERVICE_RADIUS_KM, SUPPORTED_CAMPUSES
from app.models.domain import Campus


def list_campuses() -> List[Campus]:
    return [
        Campus(
            name=c["name"],
            center_lat=c["centerLat"],
            center_lng=c["centerLng"],
            radius_km=SERVICE_RADIUS_KM,
        )
        for c in SUPPORTED_CAMPUSES
    ]


def get_campus(name: str) -> "Campus | None":
    for c in list_campuses():
        if c.name == name:
            return c
    return None


def list_pois() -> List[dict]:
    try:
        with open(OSM_POIS_PATH, "r", encoding="utf-8") as f:
            raw = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []
    result = []
    for item in raw:
        result.append({
            "name": item.get("name") or item.get("category", "未知地点"),
            "type": item.get("category", "生活服务"),
            "lat": item["lat"],
            "lng": item["lon"],
            "campus": item.get("campus", ""),
            "osmType": item.get("osm_type", ""),
            "osmId": item.get("osm_id", 0),
        })
    return result


def get_gates(campus_name: str) -> List[dict]:
    return CAMPUS_GATES.get(campus_name, [])


def list_gates() -> dict:
    return dict(CAMPUS_GATES)