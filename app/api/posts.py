"""论坛帖子处理器：发布 / 列表 / 详情 / 评论 / 点赞。"""
from app.models.schemas import ErrorCode, err, ok
from app.services import comment_service, like_service, post_service, trip_service


def create_post(h, body, path_params):
    _token, username, _ = h.get_session()
    req = type("PostReq", (), {
        "title": body.get("title") or "",
        "content": body.get("content") or "",
        "campusName": body.get("campusName"),
        "topic": body.get("topic"),
        "tripId": body.get("tripId"),
    })()
    code, msg, data = post_service.create_post(username, req)
    return ok(data) if code == ErrorCode.OK else err(code, msg)


def list_posts(h, body, path_params):
    h.get_session()
    campus_name = h.q("campusName") or None
    topic = h.q("topic") or None
    page = max(1, h.int_q("page", 1))
    size = min(100, max(1, h.int_q("size", 20)))
    items, total = post_service.list_posts(campus_name, topic, page, size)
    return ok({"items": items, "total": total})


def get_post(h, body, path_params):
    _token, username, _ = h.get_session()
    post = post_service.get_post(path_params["id"])
    if not post:
        return err(ErrorCode.NOT_FOUND, "帖子不存在")
    like_status = like_service.get_like_status(username, post["postId"])
    post["liked"] = like_status["liked"]
    post["likeCount"] = like_status["likeCount"]
    if post.get("tripId"):
        post["trip"] = trip_service.get_trip(post["tripId"])
    return ok(post)


def create_comment(h, body, path_params):
    _token, username, _ = h.get_session()
    post_id = path_params["id"]
    content = body.get("content") or ""
    code, msg, data = comment_service.create_comment(username, post_id, content)
    return ok(data) if code == ErrorCode.OK else err(code, msg)


def list_comments(h, body, path_params):
    h.get_session()
    comments = comment_service.list_comments(path_params["id"])
    return ok({"items": comments, "total": len(comments)})


def toggle_like(h, body, path_params):
    _token, username, _ = h.get_session()
    post_id = path_params["id"]
    result = like_service.toggle_like(username, post_id)
    return ok(result)

def delete_post(h, body, path_params):
    _token, username, _ = h.get_session()
    post_id = path_params["id"]
    code, msg, data = post_service.delete_post(username, post_id)
    return ok(data, msg) if code == ErrorCode.OK else err(code, msg)