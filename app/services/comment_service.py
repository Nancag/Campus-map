"""评论业务服务：校验 + 发布 + 列表。"""
from datetime import datetime
from typing import List, Optional, Tuple

from app.models.schemas import ErrorCode
from app.repositories import comment_repo

COMMENT_MAX_LEN = 300


def create_comment(username: str, post_id: str, content: str) -> Tuple[int, str, Optional[dict]]:
    content = (content or "").strip()
    if not content:
        return ErrorCode.POST_CONTENT_INVALID, "评论内容不能为空", None
    if len(content) > COMMENT_MAX_LEN:
        return ErrorCode.POST_CONTENT_INVALID, f"评论内容不能超过{COMMENT_MAX_LEN}个字符", None

    import uuid

    comment = {
        "commentId": "c_" + uuid.uuid4().hex[:12],
        "postId": post_id,
        "username": username,
        "content": content,
        "createdAt": datetime.now().isoformat(),
    }
    comment_repo.create(comment)
    return ErrorCode.OK, "ok", {"commentId": comment["commentId"]}


def list_comments(post_id: str) -> List[dict]:
    return comment_repo.list_by_post(post_id)