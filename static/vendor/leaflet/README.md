# Leaflet 本地化说明

本目录用于存放 Leaflet 本地化资源，以实现离线可用（可选）。

前端 `index.html` 的加载策略：
1. 优先加载本目录的 `leaflet.css` / `leaflet.js`；
2. 若本目录文件缺失，回退到免费 CDN（unpkg）；
3. 若 CDN 仍不可用，前端自动降级为「文字地点 + 列表模式」（不依赖地图，功能不受影响）。

如需完全离线，请手动下载以下两个文件放置到本目录：
- `leaflet.js`   ← https://unpkg.com/leaflet@1.9.4/dist/leaflet.js
- `leaflet.css`  ← https://unpkg.com/leaflet@1.9.4/dist/leaflet.css

> 注意：地图瓦片来自 OpenStreetMap 公共瓦片源（免费、无需 Key），需联网加载；瓦片无法离线，属正常现象。