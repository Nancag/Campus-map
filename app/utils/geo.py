"""地理工具：Haversine 距离计算与范围判定（纯本地计算，零付费 API）。"""
import math

EARTH_RADIUS_KM = 6371.0088


def _to_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        raise ValueError("非法经纬度")


def haversine_km(lat1, lng1, lat2, lng2):
    """计算两经纬度点间大圆距离（公里）。坐标非法时抛出 ValueError。"""
    lat1, lng1, lat2, lng2 = _to_float(lat1), _to_float(lng1), _to_float(lat2), _to_float(lng2)
    if not (-90.0 <= lat1 <= 90.0 and -90.0 <= lat2 <= 90.0):
        raise ValueError("非法纬度")
    if not (-180.0 <= lng1 <= 180.0 and -180.0 <= lng2 <= 180.0):
        raise ValueError("非法经度")

    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lng2 - lng1)

    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return EARTH_RADIUS_KM * c


def within_radius(lat1, lng1, lat2, lng2, radius_km):
    """判断两点距离是否在 radius_km 范围内。"""
    return haversine_km(lat1, lng1, lat2, lng2) <= radius_km