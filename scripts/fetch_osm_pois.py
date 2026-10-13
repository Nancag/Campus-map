"""从 OpenStreetMap Overpass API 获取校区周边真实 POI 数据。

用法：
    python scripts/fetch_osm_pois.py

结果保存到 data/osm_pois.json，地图页面读取本地缓存，不自动请求 API。
"""
import json
import os
import sys
import ssl
import urllib.request
import urllib.parse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import SUPPORTED_CAMPUSES, OSM_POIS_PATH

OVERPASS_URLS = [
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass-api.de/api/interpreter",
    "https://overpass.openstreetmap.ru/api/interpreter",
]
QUERY_RADIUS_M = 5000
TIMEOUT = 120

TAG_FILTERS = [
    ('amenity', 'hospital', '医院'),
    ('amenity', 'clinic', '医院'),
    ('amenity', 'school', '学校'),
    ('amenity', 'college', '学校'),
    ('amenity', 'university', '学校'),
    ('shop', 'mall', '商场'),
    ('shop', 'supermarket', '商场'),
    ('shop', 'convenience', '店铺'),
    ('amenity', 'restaurant', '店铺'),
    ('amenity', 'cafe', '店铺'),
    ('leisure', 'park', '公园'),
    ('leisure', 'garden', '公园'),
    ('highway', 'bus_stop', '公共交通'),
    ('public_transport', 'platform', '公共交通'),
    ('public_transport', 'station', '公共交通'),
    ('amenity', 'pharmacy', '生活服务'),
    ('amenity', 'bank', '生活服务'),
    ('amenity', 'post_office', '生活服务'),
    ('amenity', 'police', '生活服务'),
]


def build_query(lat, lng, radius):
    parts = []
    for key, val, _cat in TAG_FILTERS:
        parts.append(f'node(around:{radius},{lat},{lng})["{key}"="{val}"];')
        parts.append(f'way(around:{radius},{lat},{lng})["{key}"="{val}"];')
    body = "\n  ".join(parts)
    return f"""[out:json][timeout:{TIMEOUT}];
(
  {body}
);
out center tags;"""


def query_overpass(lat, lng, campus_name):
    query = build_query(lat, lng, QUERY_RADIUS_M)
    data = urllib.parse.urlencode({"data": query}).encode("utf-8")
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    print(f"  查询 {campus_name} 周边 {QUERY_RADIUS_M}m ...")
    last_err = None
    for url in OVERPASS_URLS:
        try:
            req = urllib.request.Request(url, data=data, method="POST")
            req.add_header("User-Agent", "CampusMap/1.0")
            with urllib.request.urlopen(req, context=ctx, timeout=TIMEOUT) as resp:
                raw = json.loads(resp.read().decode("utf-8"))
            elements = raw.get("elements", [])
            print(f"  返回 {len(elements)} 个元素（{url}）")
            return elements
        except Exception as e:
            print(f"  失败（{url}）: {e}")
            last_err = e
    raise last_err


def categorize(tags):
    for key, val, cat in TAG_FILTERS:
        if tags.get(key) == val:
            return cat
    return None


def parse_elements(elements, campus_name):
    results = []
    for el in elements:
        tags = el.get("tags", {})
        category = categorize(tags)
        if category is None:
            continue
        if el["type"] == "node":
            lat = el.get("lat")
            lon = el.get("lon")
        else:
            center = el.get("center", {})
            lat = center.get("lat")
            lon = center.get("lon")
        if lat is None or lon is None:
            continue
        name = tags.get("name", tags.get("name:zh", ""))
        results.append({
            "osm_type": el["type"],
            "osm_id": el["id"],
            "name": name,
            "lat": round(lat, 6),
            "lon": round(lon, 6),
            "category": category,
            "campus": campus_name,
            "tags": dict(tags),
        })
    return results


def deduplicate(pois):
    seen = set()
    result = []
    for p in pois:
        key = (p["osm_type"], p["osm_id"])
        if key in seen:
            continue
        seen.add(key)
        result.append(p)
    return result


def main():
    all_pois = []
    for campus in SUPPORTED_CAMPUSES:
        elements = query_overpass(
            campus["centerLat"], campus["centerLng"], campus["name"]
        )
        parsed = parse_elements(elements, campus["name"])
        all_pois.extend(parsed)

    before_dedup = len(all_pois)
    all_pois = deduplicate(all_pois)
    after_dedup = len(all_pois)

    cat_counts = {}
    for p in all_pois:
        cat_counts[p["category"]] = cat_counts.get(p["category"], 0) + 1

    print(f"\n去重前: {before_dedup}，去重后: {after_dedup}")
    for cat, cnt in sorted(cat_counts.items()):
        print(f"  {cat}: {cnt}")

    os.makedirs(os.path.dirname(OSM_POIS_PATH), exist_ok=True)
    with open(OSM_POIS_PATH, "w", encoding="utf-8") as f:
        json.dump(all_pois, f, ensure_ascii=False, indent=2)
    print(f"\n已保存到 {OSM_POIS_PATH}（{after_dedup} 个 POI）")

    return all_pois


if __name__ == "__main__":
    main()