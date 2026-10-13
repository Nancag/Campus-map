"""点赞仓储：切换点赞、查询状态、计数。"""
from typing import Optional

from app.models import db


def toggle(post_id: str, username: str, created_at: str) -> bool:
    """切换点赞状态。返回 True=已点赞, False=已取消。"""
    conn = db.get_conn()
    try:
        cur = conn.execute(
            "DELETE FROM post_likes WHERE post_id = ? AND username = ?",
            (post_id, username),
        )
        if cur.rowcount > 0:
            conn.commit()
            return False
        conn.execute(
            "INSERT INTO post_likes (post_id, username, created_at) VALUES (?,?,?)",
            (post_id, username, created_at),
        )
        conn.commit()
        return True
    finally:
        conn.close()


def is_liked(post_id: str, username: str) -> bool:
    conn = db.get_conn()
    try:
        row = conn.execute(
            "SELECT 1 FROM post_likes WHERE post_id = ? AND username = ?",
            (post_id, username),
        ).fetchone()
        return row is not None
    finally:
        conn.close()


def count_by_post(post_id: str) -> int:
    conn = db.get_conn()
    try:
        row = conn.execute(
            "SELECT COUNT(*) AS c FROM post_likes WHERE post_id = ?",
            (post_id,),
        ).fetchone()
        return row["c"]
    finally:
        conn.close()