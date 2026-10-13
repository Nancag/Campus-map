"""Reverse geocode campus coordinates and search for nearby universities."""
import urllib.request
import json
import sys

def fetch_json(url):
    req = urllib.request.Request(url)
    req.add_header('User-Agent', 'CampusCarpool/1.0')
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode('utf-8'))

print('=== 1. Reverse geocode: 25.8805227, 119.5566502 (current binhai) ===')
try:
    url = 'https://nominatim.openstreetmap.org/reverse?lat=25.8805227&lon=119.5566502&format=json&addressdetails=1&zoom=18'
    result = fetch_json(url)
    print(json.dumps(result, ensure_ascii=False, indent=2))
except Exception as e:
    print(f'Error: {e}')

print()
print('=== 2. Nominatim details for way 1377363486 ===')
try:
    url = 'https://nominatim.openstreetmap.org/details?osmtype=W&osmid=1377363486&format=json'
    result = fetch_json(url)
    print(json.dumps(result, ensure_ascii=False, indent=2))
except Exception as e:
    print(f'Error: {e}')

print()
print('=== 3. Search for amenity=university near 25.88, 119.55 ===')
try:
    url = 'https://nominatim.openstreetmap.org/search?amenity=university&format=json&limit=10&addressdetails=1&viewbox=119.53,25.90,119.59,25.86&bounded_viewbox=1'
    result = fetch_json(url)
    print(f'Found {len(result)} result(s):')
    for r in result:
        print(f'  {r["osm_type"]}/{r["osm_id"]}: {r["name"]} at ({r["lat"]}, {r["lon"]})')
        print(f'    {r["display_name"]}')
except Exception as e:
    print(f'Error: {e}')

print()
print('=== 4. Reverse geocode: 25.9259051, 119.4953332 (current changle) ===')
try:
    url = 'https://nominatim.openstreetmap.org/reverse?lat=25.9259051&lon=119.4953332&format=json&addressdetails=1&zoom=18'
    result = fetch_json(url)
    print(json.dumps(result, ensure_ascii=False, indent=2))
except Exception as e:
    print(f'Error: {e}')

print()
print('=== 5. Search for Wenwusha area ===')
try:
    url = 'https://nominatim.openstreetmap.org/search?q=Wenwusha+Changle&format=json&limit=5&addressdetails=1'
    result = fetch_json(url)
    for r in result:
        print(f'  {r["osm_type"]}/{r["osm_id"]}: {r["name"]} at ({r["lat"]}, {r["lon"]})')
        print(f'    {r["display_name"]}')
except Exception as e:
    print(f'Error: {e}')