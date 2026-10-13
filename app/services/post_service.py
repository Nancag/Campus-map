"""论坛帖子业务服务：发布校验、列表与详情。"""
from datetime import datetime
from typing import Optional, Tuple

from app.config import ADMIN_USERNAMES, POST_CONTENT_MAX_LEN, POST_TITLE_MAX_LEN, POST_TOPICS
from app.models.schemas import ErrorCode
from app.repositories import post_repo


def create_post(username: str, req) -> Tuple[int, str, Optional[dict]]:
    title = (req.title or "").strip()
    content = (req.content or "").strip()
    topic = (req.topic or "life").strip()

    if not title or len(title) > POST_TITLE_MAX_LEN:
        return ErrorCode.POST_TITLE_INVALID, f"标题必填且不超过{POST_TITLE_MAX_LEN}个字符", None
    if not content or len(content) > POST_CONTENT_MAX_LEN:
        return ErrorCode.POST_CONTENT_INVALID, f"内容必填且不超过{POST_CONTENT_MAX_LEN}个字符", None
    if topic not in POST_TOPICS:
        return ErrorCode.POST_TITLE_INVALID, f"主题必须是 {', '.join(POST_TOPICS)} 之一", None

    import uuid

    post = {
        "postId": "p_" + uuid.uuid4().hex[:12],
        "title": title,
        "content": content,
        "authorName": username,
        "campusName": req.campusName,
        "topic": topic,
        "tripId": getattr(req, "tripId", None),
        "createdAt": datetime.now().isoformat(),
    }
    post_repo.create(post)
    return ErrorCode.OK, "ok", {"postId": post["postId"]}


def list_posts(campus_name: Optional[str], topic: Optional[str], page: int, size: int):
    return post_repo.search(campus_name, topic, page, size)


def get_post(post_id: str) -> Optional[dict]:
    post = post_repo.find_by_id(post_id)
    if post and post.get("tripId"):
        from app.services import trip_service
        post["trip"] = trip_service.get_trip(post["tripId"])
    return post

def delete_post(username: str, post_id: str) -> Tuple[int, str, Optional[dict]]:
    post = post_repo.find_by_id(post_id)
    if not post:
        return ErrorCode.NOT_FOUND, "帖子不存在", None
    if post["authorName"] != username and username not in ADMIN_USERNAMES:
        return ErrorCode.FORBIDDEN, "无权限删除该帖子", None
    post_repo.soft_delete(post_id)
    return ErrorCode.OK, "帖子删除成功", None