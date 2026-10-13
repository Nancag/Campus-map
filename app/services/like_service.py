"""点赞业务服务：切换 + 查询。"""
from datetime import datetime
from typing import Optional

from app.repositories import like_repo


def toggle_like(username: str, post_id: str) -> dict:
    now = datetime.now().isoformat()
    liked = like_repo.toggle(post_id, username, now)
    count = like_repo.count_by_post(post_id)
    return {"liked": liked, "likeCount": count}


def get_like_status(username: str, post_id: str) -> dict:
    liked = like_repo.is_liked(post_id, username)
    count = like_repo.count_by_post(post_id)
    return {"liked": liked, "likeCount": count}