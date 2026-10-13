"""SQLite 连接管理与表结构定义（基于标准库 sqlite3，无外部依赖）。"""
import os
import sqlite3
import threading

from app.config import DB_PATH, SUPPORTED_CAMPUSES, SERVICE_RADIUS_KM

_lock = threading.Lock()

SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    token       TEXT PRIMARY KEY,
    username    TEXT NOT NULL,
    gender      TEXT NOT NULL DEFAULT '保密',
    expires_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS trips (
    trip_id          TEXT PRIMARY KEY,
    team_name        TEXT NOT NULL DEFAULT '',
    origin           TEXT NOT NULL,
    destination      TEXT NOT NULL,
    origin_lat       REAL,
    origin_lng       REAL,
    destination_lat  REAL,
    destination_lng  REAL,
    depart_at        TEXT NOT NULL,
    max_seats        INTEGER NOT NULL,
    current_seats    INTEGER NOT NULL,
    fee              REAL,
    leader           TEXT NOT NULL,
    status           TEXT NOT NULL,
    gender           TEXT NOT NULL DEFAULT '不限',
    remark           TEXT,
    created_at       TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS trip_members (
    trip_id      TEXT NOT NULL,
    username     TEXT NOT NULL,
    gender       TEXT NOT NULL DEFAULT '保密',
    joined_at    TEXT NOT NULL,
    PRIMARY KEY (trip_id, username)
);

CREATE TABLE IF NOT EXISTS team_forum_posts (
    post_id      TEXT PRIMARY KEY,
    trip_id      TEXT NOT NULL,
    created_at   TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS posts (
    post_id      TEXT PRIMARY KEY,
    title        TEXT NOT NULL,
    content      TEXT NOT NULL,
    author       TEXT NOT NULL,
    campus_name  TEXT,
    created_at   TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS comments (
    comment_id  TEXT PRIMARY KEY,
    post_id     TEXT NOT NULL,
    username    TEXT NOT NULL,
    content     TEXT NOT NULL,
    created_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS post_likes (
    post_id     TEXT NOT NULL,
    username    TEXT NOT NULL,
    created_at  TEXT NOT NULL,
    PRIMARY KEY (post_id, username)
);

CREATE TABLE IF NOT EXISTS campuses (
    name        TEXT PRIMARY KEY,
    center_lat  REAL NOT NULL,
    center_lng  REAL NOT NULL,
    radius_km   REAL NOT NULL
);
"""


def get_conn() -> sqlite3.Connection:
    """获取一个新的 SQLite 连接；自动创建数据目录。"""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _ensure_column(conn, table: str, column: str, decl: str) -> None:
    """旧表缺列时按需补充（兼容历史数据库）。"""
    cols = [r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()]
    if column not in cols:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {decl}")


def init_db() -> None:
    """建表并幂等初始化校区数据。"""
    with _lock:
        conn = get_conn()
        try:
            conn.executescript(SCHEMA)
            _ensure_column(conn, "sessions", "gender", "TEXT NOT NULL DEFAULT '保密'")
            _ensure_column(conn, "trips", "gender", "TEXT NOT NULL DEFAULT '不限'")
            _ensure_column(conn, "trips", "remark", "TEXT")
            _ensure_column(conn, "trips", "team_name", "TEXT NOT NULL DEFAULT ''")
            _ensure_column(conn, "posts", "topic", "TEXT NOT NULL DEFAULT 'life'")
            for campus in SUPPORTED_CAMPUSES:
                conn.execute(
                    "INSERT OR REPLACE INTO campuses (name, center_lat, center_lng, radius_km) "
                    "VALUES (?, ?, ?, ?)",
                    (
                        campus["name"],
                        campus["centerLat"],
                        campus["centerLng"],
                        SERVICE_RADIUS_KM,
                    ),
                )
            conn.commit()
        finally:
            conn.close()