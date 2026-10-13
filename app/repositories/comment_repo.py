"""评论仓储：插入、按帖子检索、计数。"""
from typing import List, Optional, Tuple

from app.models import db


def _row_to_comment(row) -> dict:
    return {
        "commentId": row["comment_id"],
        "postId": row["post_id"],
        "username": row["username"],
        "content": row["content"],
        "createdAt": row["created_at"],
    }


def create(comment: dict) -> None:
    conn = db.get_conn()
    try:
        conn.execute(
            "INSERT INTO comments (comment_id, post_id, username, content, created_at) "
            "VALUES (?,?,?,?,?)",
            (
                comment["commentId"],
                comment["postId"],
                comment["username"],
                comment["content"],
                comment["createdAt"],
            ),
        )
        conn.commit()
    finally:
        conn.close()


def list_by_post(post_id: str) -> List[dict]:
    conn = db.get_conn()
    try:
        rows = conn.execute(
            "SELECT * FROM comments WHERE post_id = ? ORDER BY created_at ASC",
            (post_id,),
        ).fetchall()
        return [_row_to_comment(r) for r in rows]
    finally:
        conn.close()


def count_by_post(post_id: str) -> int:
    conn = db.get_conn()
    try:
        row = conn.execute(
            "SELECT COUNT(*) AS c FROM comments WHERE post_id = ?",
            (post_id,),
        ).fetchone()
        return row["c"]
    finally:
        conn.close()