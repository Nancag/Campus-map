# Campus map · 校园拼车平台（Demo 简化版）

面向高校学生的校园出行互助平台：通过地图定位、地点标记、拼车队伍创建与加入，帮助学生快速找到同行伙伴。

## 技术栈（零第三方依赖 · 免费开源 · 零付费 API）

| 层面 | 选型 |
|------|------|
| 后端 | Python 标准库 `http.server` + `sqlite3`（无任何第三方依赖） |
| 存储 | SQLite（标准库 sqlite3，零部署） |
| 前端 | 原生 HTML/CSS/JS + Leaflet + OpenStreetMap 免费瓦片 |
| 地理校验 | 自研 Haversine 公式（纯本地计算） |

## 快速启动（无需安装任何依赖）

```bash
cd campus_carpool

# 方式一：一键启动
python scripts/deploy.py

# 方式二：直接启动
python -m app.main
```

访问 `http://127.0.0.1:8000` 即可使用。

初始化示例数据（1 条队伍 + 1 条帖子）：

```bash
python scripts/seed.py
```

## 接口清单（13 个）

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/guest/enter` | 游客进入（仅昵称） |
| GET | `/api/campuses` | 获取支持校区与范围 |
| POST | `/api/trips` | 发布拼车队伍 |
| GET | `/api/trips` | 搜索拼车队伍 |
| GET | `/api/trips/{id}` | 队伍详情 |
| POST | `/api/trips/{id}/join` | 加入队伍 |
| POST | `/api/trips/{id}/leave` | 退出队伍 |
| POST | `/api/trips/{id}/depart` | 队长标记出发 |
| POST | `/api/trips/{id}/complete` | 队长标记完成 |
| POST | `/api/trips/{id}/cancel` | 队长取消队伍 |
| POST | `/api/posts` | 发布帖子 |
| GET | `/api/posts` | 帖子列表（可按校区过滤） |
| GET | `/api/posts/{id}` | 帖子详情 |

除「游客进入」外，其余接口均需请求头 `Authorization: Bearer <token>`。

统一响应结构：`{ "code": 0, "message": "ok", "data": ... }`，`code=0` 表示成功。

## 测试（标准库 unittest，无需 pytest）

```bash
# 单元测试
python -m unittest discover -s tests -v

# 服务层端到端集成验证（无需网络）
python scripts/smoke_test.py
```

## 边界说明（Demo 简化范围）

- **仅游客模式**：无注册/实名，不提供手机号、邮箱、第三方登录；仅校验用户名必填且 ≤20 字符。
- **不保存个人数据**：仅以用户名作为会话内临时标识，不采集手机号、学号、证件号等任何个人数据。
- **范围约束**：仅支持福州外语外贸学院滨海校区、长乐校区；地图展示与业务范围限定学校周边 40km，其他高校暂不开放。
- **无订单/评价系统**：拼车以「队伍 + 席位计数」表达；论坛帖子仅发布/浏览（无回复）。
- 「防重复加入」采用会话级内存态集合，服务重启后会重置（席位计数仍持久化），属 Demo 已知限制。

## 目录结构

```
campus_carpool/
├── app/            # 后端（models/services/repositories/api/utils + http.py 服务）
├── static/         # 前端单页（index.html/style.css/app.js/vendor）
├── data/           # SQLite 数据文件（运行时生成）
├── tests/          # unittest 单元测试
├── scripts/        # deploy.py（启动编排）、seed.py（示例数据）
├── requirements.txt
└── README.md
```