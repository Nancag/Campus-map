"""校门人工确认配置：读取/保存 campus_gates.json。"""
import json
import os

from app.config import APP_DIR
from app.models.schemas import ErrorCode, err, ok

GATES_FILE = os.path.join(APP_DIR, "data", "campus_gates.json")


def list_gates(h, body, path_params):
    h.get_session()
    if not os.path.exists(GATES_FILE):
        return ok({})
    try:
        with open(GATES_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return ok(data)
    except Exception as e:
        return err(ErrorCode.INTERNAL, "读取校门配置失败: %s" % str(e))


def save_gate(h, body, path_params):
    _token, username, _ = h.get_session()
    campus = body.get("campus")
    gate_name = body.get("gateName")
    lng = body.get("lng")
    lat = body.get("lat")
    if not campus or not gate_name or lng is None or lat is None:
        return err(ErrorCode.TRIP_FIELD_MISSING, "campus/gateName/lng/lat 必填")

    data = {}
    if os.path.exists(GATES_FILE):
        try:
            with open(GATES_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            data = {}

    if campus not in data:
        data[campus] = {}

    data[campus][gate_name] = {
        "lng": float(lng),
        "lat": float(lat),
        "verified": True,
        "source": "manual_verified_amap",
        "verifiedBy": username,
    }

    try:
        os.makedirs(os.path.dirname(GATES_FILE), exist_ok=True)
        with open(GATES_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return ok(data)
    except Exception as e:
        return err(ErrorCode.INTERNAL, "保存校门配置失败: %s" % str(e))