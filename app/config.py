"""全局配置模块：校区坐标、范围半径、POI 地点、校区入口、长度限制、数据库路径等常量。"""
import os

# 支持校区（第一阶段）：中心坐标为示例值，需实测校准
SUPPORTED_CAMPUSES = [
    {"name": "福州外语外贸学院滨海校区", "centerLat": 25.8805227, "centerLng": 119.5566502},
    {"name": "福州外语外贸学院长乐校区", "centerLat": 25.9259051, "centerLng": 119.4953332},
]

# 地图/业务服务半径（公里）
SERVICE_RADIUS_KM = 40

# 长度限制
USERNAME_MAX_LEN = 20
POST_TITLE_MAX_LEN = 50
POST_CONTENT_MAX_LEN = 2000
REMARK_MAX_LEN = 200

# 应用根目录：campus_carpool/
APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# SQLite 数据库路径（可经环境变量 CAMPUS_CARPOOL_DB 覆盖）
DB_PATH = os.environ.get(
    "CAMPUS_CARPOOL_DB",
    os.path.join(APP_DIR, "data", "campus_carpool.db"),
)

# 会话有效期（秒），默认 24 小时
SESSION_TTL_SECONDS = int(os.environ.get("CAMPUS_CARPOOL_SESSION_TTL", 24 * 3600))

# 静态资源目录
STATIC_DIR = os.path.join(APP_DIR, "static")

# POI 地点类型
POI_TYPES = ["公园", "商场", "店铺", "医院", "学校", "公共交通", "生活服务"]

# 校区入口（出发地点，默认「学校入口」）
CAMPUS_GATES = {
    "福州外语外贸学院滨海校区": [
        {"name": "学校入口", "lat": 25.8805227, "lng": 119.5566502},
    ],
    "福州外语外贸学院长乐校区": [
        {"name": "学校入口", "lat": 25.9259051, "lng": 119.4953332},
    ],
}

# OSM 真实 POI 缓存文件路径
OSM_POIS_PATH = os.path.join(APP_DIR, "data", "osm_pois.json")

# 队伍性别要求
GENDER_NONE = "不限"
GENDER_FEMALE_ONLY = "仅女生"
GENDER_MALE_ONLY = "仅男生"
TEAM_GENDERS = [GENDER_NONE, GENDER_FEMALE_ONLY, GENDER_MALE_ONLY]

# 队伍人数上限
MAX_SEATS = 5

# 队名长度限制
TEAM_NAME_MAX_LEN = 30

# 校门名称（前端通过高德 PlaceSearch 搜索真实 POI 坐标）
CAMPUS_GATE_NAMES = {
    "福州外语外贸学院滨海校区": ["北门", "南门"],
    "福州外语外贸学院长乐校区": ["北门", "南门", "东门", "西门"],
}

# 论坛帖子主题（英文 key 存储，前端映射中文标签）
POST_TOPICS = ["carpool", "life", "market", "activity", "study", "lost_found"]