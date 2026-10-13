"""通过 OSM Nominatim details API 获取校区 way 的 polygon geometry 并缓存到本地 JSON。

用法：
    python scripts/fetch_campus_boundaries.py

数据源：
    https://nominatim.openstreetmap.org/details?osmtype=W&osmid={way_id}&format=json&polygon_geojson=1

输出：
    data/campus_boundaries.json
"""
import json
import os
import sys
import urllib.request
from datetime import datetime, timezone

APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_PATH = os.path.join(APP_DIR, "data", "campus_boundaries.json")

CAMPUSES = [
    {
        "campus_id": "binhai",
        "name": "福州外语外贸学院滨海校区",
        "osm_type": "way",
        "osm_id": 1377363486,
        "current_center": (25.8805227, 119.5566502),
    },
    {
        "campus_id": "changle",
        "name": "福州外语外贸学院长乐校区",
        "osm_type": "way",
        "osm_id": 1000502436,
        "current_center": (25.9259051, 119.4953332),
    },
]

NOMINATIM_DETAILS_URL = "https://nominatim.openstreetmap.org/details"


def fetch_way_polygon(osm_id: int) -> dict:
    url = f"{NOMINATIM_DETAILS_URL}?osmtype=W&osmid={osm_id}&format=json&polygon_geojson=1"
    req = urllib.request.Request(url)
    req.add_header("User-Agent", "CampusCarpool/1.0")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def validate_polygon(coords_lonlat: list, campus_name: str) -> dict:
    result = {"valid": True, "errors": []}

    if not coords_lonlat or len(coords_lonlat) < 4:
        result["valid"] = False
        result["errors"].append(f"{campus_name}: geometry 为空或节点数 < 4")
        return result

    first = coords_lonlat[0]
    last = coords_lonlat[-1]
    if abs(first[0] - last[0]) > 1e-9 or abs(first[1] - last[1]) > 1e-9:
        result["valid"] = False
        result["errors"].append(f"{campus_name}: polygon 首尾不闭合")

    for i, pt in enumerate(coords_lonlat):
        lon, lat = pt[0], pt[1]
        if not (10.0 < lat < 60.0 and 70.0 < lon < 140.0):
            result["valid"] = False
            result["errors"].append(
                f"{campus_name}: 节点[{i}] 经纬度超出中国范围 lat={lat}, lon={lon}"
            )
            break

    node_count = len(coords_lonlat) - 1 if result["valid"] else len(coords_lonlat)
    result["node_count"] = node_count
    return result


def point_in_polygon(px: float, py: float, polygon: list) -> bool:
    n = len(polygon)
    inside = False
    j = n - 1
    for i in range(n):
        xi, yi = polygon[i][0], polygon[i][1]
        xj, yj = polygon[j][0], polygon[j][1]
        if ((yi > py) != (yj > py)) and (
            px < (xj - xi) * (py - yi) / (yj - yi) + xi
        ):
            inside = not inside
        j = i
    return inside


def polygon_centroid(polygon: list) -> tuple:
    n = len(polygon) - 1
    cx = 0.0
    cy = 0.0
    area = 0.0
    for i in range(n):
        x0, y0 = polygon[i][0], polygon[i][1]
        x1, y1 = polygon[i + 1][0], polygon[i + 1][1]
        cross = x0 * y1 - x1 * y0
        area += cross
        cx += (x0 + x1) * cross
        cy += (y0 + y1) * cross
    area /= 2.0
    if abs(area) < 1e-12:
        xs = [p[0] for p in polygon[:-1]]
        ys = [p[1] for p in polygon[:-1]]
        return (sum(ys) / len(ys), sum(xs) / len(xs))
    cx /= (6.0 * area)
    cy /= (6.0 * area)
    return (cy, cx)


def main():
    print("=== OSM 校园边界获取 ===\n")
    results = []

    for campus in CAMPUSES:
        name = campus["name"]
        osm_id = campus["osm_id"]
        current_lat, current_lon = campus["current_center"]

        print(f"--- {name} ---")
        print(f"  OSM way: {osm_id}")

        try:
            data = fetch_way_polygon(osm_id)
        except Exception as e:
            print(f"  获取失败: {e}")
            results.append({
                "campus_id": campus["campus_id"],
                "name": name,
                "osm_type": "way",
                "osm_id": osm_id,
                "geometry": [],
                "node_count": 0,
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "error": str(e),
            })
            continue

        geom = data.get("geometry", {})
        if geom.get("type") != "Polygon":
            print(f"  geometry 类型不是 Polygon: {geom.get('type')}")
            continue

        coords_lonlat = geom["coordinates"][0]
        print(f"  原始节点数: {len(coords_lonlat)}")

        validation = validate_polygon(coords_lonlat, name)
        if not validation["valid"]:
            print(f"  验证失败: {validation['errors']}")
            continue
        print(f"  验证通过: 闭合={True}, 节点数={validation['node_count']}")

        coords_latlon = [[pt[1], pt[0]] for pt in coords_lonlat]

        inside = point_in_polygon(current_lon, current_lat, coords_lonlat)
        print(f"  当前中心 ({current_lat}, {current_lon}) 在 polygon 内: {inside}")

        centroid_lat, centroid_lon = polygon_centroid(coords_lonlat)
        print(f"  polygon centroid: ({centroid_lat:.7f}, {centroid_lon:.7f})")

        centroid_inside = point_in_polygon(centroid_lon, centroid_lat, coords_lonlat)
        print(f"  centroid 在 polygon 内: {centroid_inside}")

        results.append({
            "campus_id": campus["campus_id"],
            "name": name,
            "osm_type": "way",
            "osm_id": osm_id,
            "geometry": coords_latlon,
            "node_count": validation["node_count"],
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "current_center": {"lat": current_lat, "lng": current_lon},
            "current_center_in_polygon": inside,
            "centroid": {"lat": round(centroid_lat, 7), "lng": round(centroid_lon, 7)},
            "centroid_in_polygon": centroid_inside,
        })
        print()

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"已写入: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()