"""论坛帖子删除功能测试。直接调用 service 层，使用临时数据库。"""
import os
import sys
import tempfile

tmpdir = tempfile.mkdtemp()
os.environ["CAMPUS_CARPOOL_DB"] = os.path.join(tmpdir, "test.db")
os.environ["CAMPUS_ADMIN_USERNAMES"] = "admin"

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from app.models.db import init_db
from app.models.schemas import ErrorCode
from app.services import post_service
from types import SimpleNamespace

init_db()

passed = 0
failed = 0


def check(name, ok, detail=""):
    global passed, failed
    status = "PASS" if ok else "FAIL"
    if ok:
        passed += 1
    else:
        failed += 1
    print(f"  {status}  {name}" + (f"  ({detail})" if detail else ""))


print("【论坛帖子删除功能测试】")

# 1. 作者删除自己的帖子
code, msg, data = post_service.create_post("alice", SimpleNamespace(
    title="测试帖子1", content="内容1", campusName=None, topic="life", tripId=None))
check("作者发帖成功", code == ErrorCode.OK, msg)
post_id_1 = data["postId"]

code, msg, data = post_service.delete_post("alice", post_id_1)
check("作者删除自己帖子成功", code == ErrorCode.OK, msg)

post = post_service.get_post(post_id_1)
check("删除后 get_post 返回 None", post is None, f"post={post}")

items, total = post_service.list_posts(None, None, 1, 20)
check("删除后列表不含该帖子", not any(p["postId"] == post_id_1 for p in items), f"total={total}")

# 2. 非作者删除被拒
code, msg, data = post_service.create_post("bob", SimpleNamespace(
    title="测试帖子2", content="内容2", campusName=None, topic="life", tripId=None))
check("bob 发帖成功", code == ErrorCode.OK, msg)
post_id_2 = data["postId"]

code, msg, data = post_service.delete_post("alice", post_id_2)
check("非作者删除被拒(FORBIDDEN)", code == ErrorCode.FORBIDDEN, f"code={code} msg={msg}")

post = post_service.get_post(post_id_2)
check("被拒后帖子仍存在", post is not None, f"post={post}")

# 3. 管理员删除任意帖子
code, msg, data = post_service.delete_post("admin", post_id_2)
check("管理员删除成功", code == ErrorCode.OK, msg)

post = post_service.get_post(post_id_2)
check("管理员删除后帖子不存在", post is None, f"post={post}")

# 4. 删除不存在的帖子
code, msg, data = post_service.delete_post("alice", "p_nonexistent")
check("删除不存在的帖子返回 NOT_FOUND", code == ErrorCode.NOT_FOUND, f"code={code} msg={msg}")

# 5. 删除后列表正常
code, msg, data = post_service.create_post("carol", SimpleNamespace(
    title="测试帖子3", content="内容3", campusName=None, topic="carpool", tripId=None))
check("carol 发帖成功", code == ErrorCode.OK, msg)
post_id_3 = data["postId"]

items, total = post_service.list_posts(None, None, 1, 20)
check("列表包含未删除帖子", any(p["postId"] == post_id_3 for p in items), f"total={total}")

print(f"\n{'='*50}")
print(f"总计: {passed} PASS / {failed} FAIL")
print(f"{'='*50}")
sys.exit(0 if failed == 0 else 1)