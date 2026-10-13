# 编码任务列表

> 本文档基于 `spec.md`（需求规格）与 `design.md`（技术设计 v2.0）生成，将技术设计方案转化为可执行、可验收的任务清单。
>
> **项目信息**
> - 项目目录：`campus_carpool/`
> - 技术栈：Python http.server + sqlite3（后端）、原生 JS + 高德地图 JS API 2.0（前端）
> - 启动命令：`cd campus_carpool && python -m app.main`（端口 8000）
> - 改动范围：仅前端 `static/map_amap.js`、`static/map_amap.html`、`static/map_amap.css` 三个文件
> - 后端 API 已全部就绪，无需新增后端代码
>
> **本次增量设计范围**（来自 design.md v2.0）：
> 1. 高德版底图图层切换（spec 5.3）：使用 `AMap.TileLayer` 加载 OSM/ESRI 外部瓦片，自定义 HTML 控件实现切换 UI
> 2. 死代码清理（spec 5.2）：删除 Phase 1 测试页遗留的 `renderCampusReport` / `renderGateReport` 函数
>
> **已实现不在本次范围**：行程生命周期操作（spec 5.1）、Phase 2 全部功能（spec 7-8）均已在 `static/map_amap.js` 中实现并通过验收。
>
> **不修改范围**：后端 API（`app/` 目录）、SQLite schema、Leaflet 版（`map.html`/`map.js`/`map.css`）、论坛模块、游客进入机制、`osm_pois.json`、首页入口。
>
> **改动量预估**：JS +60/-62 行、HTML +8 行、CSS +30 行
>
> **任务编号规则**：T01～T04 为主任务组，子任务用 T01.1、T01.2 等编号，按依赖关系排序，前置任务必须在后续任务之前完成。
>
> **函数命名约定**：全部使用 camelCase（对应 spec 4.4.1 与用户偏好）。

---

## T01. 高德版底图图层切换

> 对应 spec 5.3 底图图层切换与 design 2.1～2.6。在 `/map_amap.html` 高德地图页新增 OSM 街道 / ESRI 卫星底图切换能力，使用 `AMap.TileLayer` 加载外部瓦片，自定义 HTML 控件实现切换 UI，切换时保留校区标记、校门标记、选中 Marker 等叠加层不变。

### T01.1 扩展 state 状态字段

- [ ] 在 `static/map_amap.js` 第 23-38 行 `state` 对象中新增两个字段：`currentBaseLayer: "osm"`（当前底图图层标识，取值 `"osm"` | `"satellite"`，初始值为 `"osm"`）和 `baseLayerInstance: null`（当前瓦片图层实例，`AMap.TileLayer` 类型，初始值为 null）

**涉及文件**：`static/map_amap.js`（state 定义区第 23-38 行）
**预估改动量**：+2 行
**依赖**：无
**验收标准**：`state.currentBaseLayer` 初始值为 `"osm"`；`state.baseLayerInstance` 初始值为 null；不影响现有 state 字段

### T01.2 实现 OSM 与 ESRI 瓦片图层创建函数

- [ ] 在 `static/map_amap.js` 中新增 `createOSMTileLayer()` 函数，返回 `new AMap.TileLayer({ tileUrl: "https://tile.openstreetmap.org/{z}/{x}/{y}.png", zIndex: 0 })`，使用 OpenStreetMap 标准瓦片服务 URL（格式 `{z}/{x}/{y}`）
- [ ] 在 `static/map_amap.js` 中新增 `createESRITileLayer()` 函数，返回 `new AMap.TileLayer({ tileUrl: "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}", zIndex: 0 })`，使用 ESRI ArcGIS Online World_Imagery 服务 URL（注意格式为 `{z}/{y}/{x}`，y 在 x 前，与 OSM 不同）
- [ ] 两个函数均不将瓦片图层添加到地图，仅创建并返回实例，由调用方决定何时添加

**涉及文件**：`static/map_amap.js`（新增函数，建议置于 `onAmapReady` 上方或 `calcDistance` 附近）
**预估改动量**：+12 行
**依赖**：无
**验收标准**：`createOSMTileLayer()` 返回 `AMap.TileLayer` 实例且 tileUrl 指向 OSM 标准瓦片；`createESRITileLayer()` 返回 `AMap.TileLayer` 实例且 tileUrl 指向 ESRI World_Imagery 瓦片（URL 格式 `{z}/{y}/{x}`）

### T01.3 实现底图切换核心函数 switchBaseLayer

- [ ] 在 `static/map_amap.js` 中新增 `switchBaseLayer(layer)` 函数，入参 `layer` 为 `"osm"` 或 `"satellite"`
- [ ] 实现重复切换防护：当 `layer === state.currentBaseLayer` 时直接 return，不重复创建图层
- [ ] 实现旧图层移除：若 `state.baseLayerInstance` 存在，调用 `state.map.removeLayer(state.baseLayerInstance)` 移除当前底图瓦片图层
- [ ] 实现新图层创建与添加：根据 `layer` 参数调用 `createOSMTileLayer()` 或 `createESRITileLayer()` 创建新瓦片图层实例，调用 `newLayer.setMap(state.map)` 或 `state.map.addLayer(newLayer)` 添加到地图
- [ ] 实现瓦片加载失败监听：对新图层实例监听 `tileerror` 事件，`console.warn` 记录前 5 次失败 URL，控件保持可用（不自动切回）
- [ ] 实现状态更新：`state.baseLayerInstance = newLayer`、`state.currentBaseLayer = layer`
- [ ] 实现叠加层保留：切换时不调用 `clearMarkers()` / `clearSelectedMarker()` 等清理函数，校区标记、校门标记、选中 Marker 保持不变
- [ ] 实现异常捕获：瓦片创建或添加异常时 `try-catch` 捕获，`console.error` 记录日志，保持当前底图不变
- [ ] 实现控件选中态同步：更新 `#layer-osm-btn` 与 `#layer-satellite-btn` 的 `.active` CSS 类，当前图层按钮添加 `.active`，另一个移除 `.active`
- [ ] 输出操作日志：`console.log("[switchBaseLayer] 切换至", layer)`

**涉及文件**：`static/map_amap.js`（新增函数）
**预估改动量**：+20 行
**依赖**：T01.1（state 字段）、T01.2（瓦片创建函数）
**验收标准**：切换至 `"satellite"` 后底图变为 ESRI 卫星影像且 `state.currentBaseLayer === "satellite"`；切换回 `"osm"` 后底图变为 OSM 街道；切换时叠加层（校区标记、校门标记、选中 Marker）保持不变且位置正确；瓦片加载失败时控件保持可用；重复点击当前图层不产生重复创建

### T01.4 新增图层切换控件 HTML DOM

- [ ] 在 `static/map_amap.html` 第 42 行 `#map` div 之后、第 43 行 `#poi-confirm-card` 之前，新增 `#layer-switcher` 图层切换控件 DOM
- [ ] DOM 结构为：`<div id="layer-switcher" class="layer-switcher"><button id="layer-osm-btn" class="layer-btn active">OSM 街道</button><button id="layer-satellite-btn" class="layer-btn">ESRI 卫星</button></div>`
- [ ] "OSM 街道"按钮默认添加 `active` 类（默认选中态）
- [ ] 按钮添加 `onclick` 事件绑定：`onclick="switchBaseLayer('osm')"` 与 `onclick="switchBaseLayer('satellite')"`

**涉及文件**：`static/map_amap.html`（第 42-43 行之间插入）
**预估改动量**：+8 行
**依赖**：T01.3（switchBaseLayer 函数）
**验收标准**：地图页加载后右上角显示图层切换控件，含"OSM 街道"与"ESRI 卫星"两个按钮；"OSM 街道"按钮默认高亮选中；点击按钮触发 `switchBaseLayer` 调用

### T01.5 新增图层切换控件 CSS 样式

- [ ] 在 `static/map_amap.css` 中新增 `.layer-switcher` 及子元素样式，控件浮于地图右上角（`position: absolute; top: 10px; right: 10px; z-index: 1000;`）
- [ ] 控件容器样式：白色半透明背景（`background: rgba(255,255,255,0.9)`）、圆角（`border-radius: 4px`）、内边距、轻投影（`box-shadow: 0 2px 6px rgba(0,0,0,0.15)`）、`display: flex` 横向排列按钮
- [ ] 按钮基础样式 `.layer-btn`：无边框（`border: none`）、浅色背景、内边距、cursor pointer、字体大小 13px、过渡效果（`transition: all 0.2s`）
- [ ] 按钮选中态样式 `.layer-btn.active`：天蓝色背景（`background: #4fc3f7`，对应浅色主题偏好）、白色文字
- [ ] 按钮悬停效果 `.layer-btn:hover`：浅灰背景（`background: #e8f4fd`），增强可点击感知
- [ ] 控件不遮挡地图核心区域，与高德 ToolBar（RT 位置）区域协调

**涉及文件**：`static/map_amap.css`（文件末尾追加）
**预估改动量**：+30 行
**依赖**：T01.4（HTML DOM）
**验收标准**：控件浮于地图右上角，视觉风格与现有浅色主题一致（白/浅蓝）；两个按钮互斥选中，选中按钮天蓝色高亮；鼠标悬停有反馈效果；不遮挡地图核心区域与左侧栏

### T01.6 实现图层切换控件初始化函数 initAmapLayerSwitcher

- [ ] 在 `static/map_amap.js` 中新增 `initAmapLayerSwitcher()` 函数，无入参，在 `onAmapReady()` 中地图实例创建且控件添加后调用
- [ ] 实现默认 OSM 图层创建：调用 `createOSMTileLayer()` 创建 OSM 瓦片图层实例，调用 `osmLayer.setMap(state.map)` 添加到地图作为默认底图
- [ ] 实现状态初始化：`state.currentBaseLayer = "osm"`、`state.baseLayerInstance = osmLayer`
- [ ] 实现默认图层瓦片加载失败监听：监听 `tileerror` 事件，`console.warn` 记录前 5 次失败 URL
- [ ] 实现异常捕获：`try-catch` 包裹初始化逻辑，`AMap.TileLayer` 初始化异常或 DOM 元素缺失时 `console.error` 记录日志，地图保持高德默认底图，控件不显示（`#layer-switcher` 隐藏）
- [ ] 输出初始化日志：`console.log("[initAmapLayerSwitcher] 图层切换控件初始化完成，默认底图: OSM 街道")`

**涉及文件**：`static/map_amap.js`（新增函数）
**预估改动量**：+18 行
**依赖**：T01.1（state 字段）、T01.2（瓦片创建函数）、T01.4（HTML DOM）、T01.5（CSS 样式）
**验收标准**：地图首次加载默认显示 OSM 街道底图；`state.currentBaseLayer === "osm"`；`#layer-switcher` 控件可见且"OSM 街道"按钮选中；初始化异常时地图以高德默认底图正常工作且不报错

### T01.7 在 onAmapReady 中集成图层切换初始化

- [ ] 在 `static/map_amap.js` 第 319 行 `state.map.addControl(new AMap.ControlBar(...))` 之后、第 321 行 `renderCampusList()` 之前，追加一行 `initAmapLayerSwitcher();` 调用
- [ ] 确保图层切换初始化在地图实例创建（第 307 行）与控件添加（第 317-319 行）之后执行，此时 `state.map` 已就绪
- [ ] 确保图层切换初始化在 `renderCampusList()` / `loadCampus()` / `handleMapClick` 绑定之前执行，避免校区标记加载时底图未就绪

**涉及文件**：`static/map_amap.js`（第 319-321 行之间插入一行）
**预估改动量**：+1 行
**依赖**：T01.6（initAmapLayerSwitcher 函数）
**验收标准**：地图页加载后自动初始化图层切换控件，默认显示 OSM 街道底图；现有校区列表加载、地图点击事件、队伍列表刷新等功能不受影响

---

## T02. 死代码清理

> 对应 spec 5.2 遗留死代码清理与 design 2.1.2（模块 A-2）。删除 `static/map_amap.js` 中 Phase 1 测试页遗留的 `renderCampusReport` / `renderGateReport` 两个未被任何活跃入口调用的函数。

### T02.1 死代码引用校验

- [ ] 在 `static/map_amap.js` 中搜索 `renderCampusReport` 的所有引用点，确认除函数定义（第 865-893 行）外无任何调用点
- [ ] 在 `static/map_amap.js` 中搜索 `renderGateReport` 的所有引用点，确认除函数定义（第 895-926 行）外无任何调用点
- [ ] 确认活跃入口引用链（`initApp()` → `onAmapReady()` → `renderCampusList()` / `loadCampus()` / `handleMapClick()` / `refreshTrips()`）均不涉及这两个函数
- [ ] 确认 `handleMapClick()` → `findNearestAmapPoiWithFallback()` → `showPoiConfirmCard()` → `confirmPoiSelection()` → `showPoiActionCard()` → `openCreateTripModal()` / `openJoinTripModal()` 活跃链不涉及这两个函数
- [ ] 在全项目范围内搜索 `renderCampusReport` / `renderGateReport`，确认其他文件（`map.js`、`forum.js`、HTML 等）均未引用

**涉及文件**：`static/map_amap.js`（仅校验不修改）
**预估改动量**：0 行
**依赖**：无
**验收标准**：校验通过，确认两个函数均未被任何活跃入口调用；若发现活跃引用则中止清理并输出引用关系报告

### T02.2 删除遗留测试报告函数

- [ ] 删除 `static/map_amap.js` 第 865-893 行 `renderCampusReport(campus, result)` 函数定义（29 行）
- [ ] 删除 `static/map_amap.js` 第 895-926 行 `renderGateReport(campus, result)` 函数定义（32 行）
- [ ] 确认删除后文件末尾保留 `initApp();` 调用（原第 928 行）
- [ ] 确认仅删除这两个函数定义，不删除其他函数或代码
- [ ] 确认不删除 `.report-section` / `.report-row` / `.report-candidates` 等可能被其他地方使用的 CSS 类（保守策略，仅删除 JS 函数定义）

**涉及文件**：`static/map_amap.js`（第 865-926 行删除）
**预估改动量**：-62 行
**依赖**：T02.1（引用校验通过）
**验收标准**：`renderCampusReport` / `renderGateReport` 函数定义被删除；`map_amap.js` 文件行数减少 62 行；`initApp()` 调用保留；其他函数与代码保持不变

---

## T03. 集成验证

> 确保两个模块改动后无回归，底图图层切换功能正常工作，死代码清理不影响活跃功能，现有 28 项 smoke_test 全通过。

### T03.1 运行 smoke_test 确认无回归

- [ ] 执行 `python scripts/smoke_test.py`（或项目对应测试命令），确认全部测试用例通过（输出 `ALL PASS ✅` 或等价成功标记）
- [ ] 确认 smoke_test 中行程状态流转用例（队长标记出发、队长标记完成、队长取消队伍、乘客退出队伍）通过
- [ ] 确认 smoke_test 中队伍创建、加入、搜索用例通过
- [ ] 确认 smoke_test 中论坛、评论、点赞用例通过

**涉及文件**：`scripts/smoke_test.py`（仅运行不修改）
**预估改动量**：0 行
**依赖**：T01.7（图层切换集成）、T02.2（死代码清理完成）
**验收标准**：smoke_test.py 退出码为 0，全部测试用例通过，无 FAIL 项

### T03.2 前端功能手动验证

- [ ] 启动后端服务（`cd campus_carpool && python -m app.main`），打开 `http://localhost:8000/map_amap.html`，以游客身份进入，确认地图页正常加载
- [ ] 确认地图右上角显示图层切换控件，含"OSM 街道"与"ESRI 卫星"两个按钮，"OSM 街道"默认选中高亮
- [ ] 确认地图首次加载默认显示 OSM 街道底图（与现有地图外观一致）
- [ ] 点击"ESRI 卫星"按钮，确认底图切换为卫星影像图层，按钮选中态切换为"ESRI 卫星"高亮
- [ ] 切换至卫星图层后，确认校区标记、校门标记、选中 Marker 等叠加层保留且位置正确（不丢失、不错位）
- [ ] 点击"OSM 街道"按钮，确认底图切回 OSM 街道图层，叠加层仍保留
- [ ] 在卫星图层下查看滨海校区区域，确认可见真实地表影像而非 OSM 上的水域色块
- [ ] 点击地图选择地点，确认地点确认卡片与操作卡片正常弹出（死代码清理不影响地点选择功能）
- [ ] 创建队伍并查看队伍列表，确认队伍详情弹窗与行程操作按钮正常显示（死代码清理不影响行程生命周期功能）
- [ ] 打开浏览器控制台，确认无 JavaScript 报错；确认图层切换操作有 `console.log` 日志输出

**涉及文件**：无（运行时验证）
**预估改动量**：0 行
**依赖**：T03.1（smoke_test 通过）
**验收标准**：图层切换控件正常显示与交互；OSM/ESRI 底图切换正常且叠加层不丢失；滨海校区在卫星图层下可见真实地表；地点选择与队伍操作功能无回归；控制台无报错

---

## T04. 代码审查与变更确认

> 最终验证确保交付质量，确认变更范围与 design.md 一致，命名规范统一，无超范围改动。

### T04.1 代码审查

- [ ] 审查 `static/map_amap.js` 新增函数命名均为 camelCase（`createOSMTileLayer`、`createESRITileLayer`、`switchBaseLayer`、`initAmapLayerSwitcher`）
- [ ] 审查新增交互逻辑在浏览器控制台输出关键操作日志（`console.log` 图层切换、`console.warn` 瓦片加载失败、`console.error` 初始化异常）
- [ ] 审查 `switchBaseLayer` 切换时不调用 `clearMarkers()` / `clearSelectedMarker()`，叠加层保留逻辑正确
- [ ] 审查 `initAmapLayerSwitcher` 异常捕获完整，初始化失败时地图以高德默认底图降级工作
- [ ] 审查死代码删除后无残留引用，`renderCampusReport` / `renderGateReport` 在全项目中无任何引用点
- [ ] 确认未引入新的未引用文件或函数，项目文件结构保持清晰

**涉及文件**：`static/map_amap.js`、`static/map_amap.html`、`static/map_amap.css`
**预估改动量**：0 行
**依赖**：T03.2（手动验证通过）
**验收标准**：命名规范一致（camelCase）；关键操作有日志；叠加层保留逻辑正确；异常降级处理完整；无新增死代码

### T04.2 变更范围确认

- [ ] 确认本次变更仅涉及三个文件：`static/map_amap.js`（修改：+60/-62 行）、`static/map_amap.html`（修改：+8 行）、`static/map_amap.css`（修改：+30 行）
- [ ] 确认未修改任何后端代码（`app/` 目录无变更）
- [ ] 确认未修改 SQLite schema 或数据库结构
- [ ] 确认未修改 Leaflet 版地图页（`static/map.html`、`static/map.js`、`static/map.css` 保持不变）
- [ ] 确认未修改论坛模块（`static/forum.html`、`static/forum.js`、`static/forum.css` 保持不变）
- [ ] 确认未修改游客进入机制相关代码
- [ ] 确认未删除 `data/osm_pois.json` 文件
- [ ] 确认未修改首页入口（`static/index.html` 保持不变，已指向 `/map_amap.html`）
- [ ] 确认未删除 `vendor/` 目录下任何第三方库文件

**涉及文件**：全项目
**预估改动量**：0 行
**依赖**：T04.1（代码审查通过）
**验收标准**：变更范围与 design.md 2.6.1 文件改动清单一致，无超范围改动；不修改范围与 design.md 2.6.3 一致

---

## 任务执行顺序与依赖关系

```
T01.1 (state 扩展) ──┬──> T01.3 (switchBaseLayer) ──> T01.4 (HTML DOM) ──> T01.5 (CSS 样式) ──┬──> T01.6 (initAmapLayerSwitcher) ──> T01.7 (集成 onAmapReady)
                     │                                                          │
T01.2 (瓦片创建函数) ─┘                                                          │
                                                                                │
T02.1 (引用校验) ──> T02.2 (删除死代码)                                          │
                                                                                │
T01.7 + T02.2 ──> T03.1 (smoke_test) ──> T03.2 (手动验证) ──> T04.1 (代码审查) ──> T04.2 (变更确认)
```

**可并行执行**：T01.1 与 T01.2 可并行；T02.1 与 T01 系列可并行（死代码清理与图层切换互不依赖）

**关键路径**：T01.1 → T01.2 → T01.3 → T01.4 → T01.5 → T01.6 → T01.7 → T03.1 → T03.2 → T04.1 → T04.2