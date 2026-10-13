"""校区边界 API：返回本地缓存的 OSM polygon 数据。"""
import json
import os

from app.config import APP_DIR

BOUNDARIES_PATH = os.path.join(APP_DIR, "data", "campus_boundaries.json")


def list_boundaries(handler, body, path_params):
    if not os.path.isfile(BOUNDARIES_PATH):
        return {"boundaries": []}
    with open(BOUNDARIES_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    return {"boundaries": data}