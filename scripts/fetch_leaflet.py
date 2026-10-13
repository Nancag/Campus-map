import urllib.request
import os
import ssl

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

base = "https://unpkg.com/leaflet@1.9.4/dist/"
target = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static", "vendor", "leaflet")

files = [
    "leaflet.js",
    "leaflet.css",
    "images/marker-icon.png",
    "images/marker-icon-2x.png",
    "images/marker-shadow.png",
    "images/layers.png",
    "images/layers-2x.png",
]

for f in files:
    url = base + f
    path = os.path.join(target, f)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, context=ctx, timeout=30) as resp:
        data = resp.read()
        with open(path, "wb") as out:
            out.write(data)
    print(f"OK: {f} ({len(data)} bytes)")
print("All done.")