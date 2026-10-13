"""论坛帖子仓储：插入、按校区过滤检索、详情查询。"""
from typing import List, Optional, Tuple

from app.models import db


def _row_to_post(row) -> dict:
    keys = row.keys()
    return {
        "postId": row["post_id"],
        "title": row["title"],
        "content": row["content"],
        "authorName": row["author"],
        "campusName": row["campus_name"],
        "topic": row["topic"] if "topic" in keys else "life",
        "createdAt": row["created_at"],
        "tripId": row["trip_id"] if "trip_id" in keys and row["trip_id"] is not None else None,
        "likeCount": row["like_count"] if "like_count" in keys else 0,
        "commentCount": row["comment_count"] if "comment_count" in keys else 0,
    }


_COUNTS = (
    " (SELECT trip_id FROM team_forum_posts WHERE post_id = p.post_id) AS trip_id,"
    " (SELECT COUNT(*) FROM post_likes WHERE post_id = p.post_id) AS like_count,"
    " (SELECT COUNT(*) FROM comments WHERE post_id = p.post_id) AS comment_count"
)


def create(post: dict) -> None:
    conn = db.get_conn()
    try:
        conn.execute(
            "INSERT INTO posts (post_id, title, content, author, campus_name, topic, created_at) "
            "VALUES (?,?,?,?,?,?,?)",
            (
                post["postId"],
                post["title"],
                post["content"],
                post["authorName"],
                post.get("campusName"),
                post.get("topic", "life"),
                post["createdAt"],
            ),
        )
        if post.get("tripId"):
            conn.execute(
                "INSERT OR IGNORE INTO team_forum_posts (post_id, trip_id, created_at) VALUES (?,?,?)",
                (post["postId"], post["tripId"], post["createdAt"]),
            )
        conn.commit()
    finally:
        conn.close()


def search(campus_name: Optional[str], topic: Optional[str], page: int, size: int) -> Tuple[List[dict], int]:
    conds = ["p.deleted = 0"]
    params: list = []
    if campus_name:
        conds.append("p.campus_name = ?")
        params.append(campus_name)
    if topic:
        conds.append("p.topic = ?")
        params.append(topic)
    cond = " WHERE " + " AND ".join(conds)

    conn = db.get_conn()
    try:
        total = conn.execute(f"SELECT COUNT(*) AS c FROM posts p{cond}", params).fetchone()["c"]
        rows = conn.execute(
            f"SELECT p.*,{_COUNTS} FROM posts p{cond} ORDER BY p.created_at DESC LIMIT ? OFFSET ?",
            params + [size, (page - 1) * size],
        ).fetchall()
        return [_row_to_post(r) for r in rows], total
    finally:
        conn.close()


def find_by_id(post_id: str) -> Optional[dict]:
    conn = db.get_conn()
    try:
        row = conn.execute(
            f"SELECT p.*,{_COUNTS} FROM posts p WHERE p.post_id = ? AND p.deleted = 0",
            (post_id,),
        ).fetchone()
        return _row_to_post(row) if row else None
    finally:
        conn.close()


def soft_delete(post_id: str) -> bool:
    conn = db.get_conn()
    try:
        cur = conn.execute(
            "UPDATE posts SET deleted = 1 WHERE post_id = ? AND deleted = 0",
            (post_id,),
        )
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()