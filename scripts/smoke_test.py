"""端到端集成验证（服务层→仓储层全链路，无需网络）。

说明：本脚本不走 HTTP socket（沙箱/受限环境可能拦截本地回环），
直接串联服务层与仓储层，验证「进入→校区→POI→发布→搜索→加入/退出→性别校验→状态流转→帖子」主链路。
"""
import os
import sys
import tempfile
from types import SimpleNamespace

os.environ["CAMPUS_CARPOOL_DB"] = os.path.join(tempfile.mkdtemp(), "test.db")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.models.db import init_db
from app.models.domain import TripStatus
from app.models.schemas import ErrorCode
from app.repositories import campus_repo, post_repo, trip_repo
from app.services import comment_service, like_service, post_service, trip_service, user_service

init_db()

results = []


def check(name, cond):
    results.append((name, cond))
    print(("PASS  " if cond else "FAIL  ") + name)


# 1. 游客进入与鉴权（返回 username, gender 元组）
token = user_service.enter("队长", "男")
username, gender = user_service.authenticate(token)
check("游客进入并签发令牌", username == "队长" and gender == "男")

# 2. 校区（2 个，含 gates）
items = campus_repo.list_campuses()
check("校区数量为 2", len(items) == 2)
gates = campus_repo.get_gates("福州外语外贸学院滨海校区")
check("滨海校区有学校入口", len(gates) >= 1)

# 3. POI 地点
pois = campus_repo.list_pois()
check("POI 地点 ≥ 16", len(pois) >= 16)

# 4. 发布队伍（含 gender/remark）
req = SimpleNamespace(
    teamName="测试队伍1", origin="滨海东门", destination="长乐南门", departAt="2099-01-01T08:00:00",
    seats=2, fee=5.0, originLat=25.8805227, originLng=119.5566502,
    destinationLat=25.9259051, destinationLng=119.4953332,
    gender="不限", remark="顺路拼车",
)
code, _m, data = trip_service.create_trip("队长", req)
check("发布队伍成功", code == ErrorCode.OK)
trip_id = data["tripId"]

# 5. 范围外发布被拒
req_out = SimpleNamespace(
    teamName="测试队伍2", origin="北京", destination="上海", departAt="2099-01-01T08:00:00",
    seats=2, fee=None, originLat=39.9, originLng=116.4,
    destinationLat=31.2, destinationLng=121.5,
    gender="不限", remark=None,
)
code, _m, _d = trip_service.create_trip("队长", req_out)
check("范围外发布被拒(2002)", code == ErrorCode.OUT_OF_RANGE)

# 6. 搜索
items, total = trip_service.list_trips(None, None, None, None, 1, 20)
check("搜索返回至少 1 条", total >= 1)

# 7. 加入本人队伍被拒
code, _m, _d = trip_service.join_trip("队长", "男", token, trip_id)
check("加入本人队伍被拒(3002)", code == ErrorCode.JOIN_OWN_TRIP)

# 8. 乘客加入成功
token2 = user_service.enter("乘客A", "女")
code, _m, _d = trip_service.join_trip("乘客A", "女", token2, trip_id)
check("乘客加入成功", code == ErrorCode.OK)

# 9. 重复加入被拒
code, _m, _d = trip_service.join_trip("乘客A", "女", token2, trip_id)
check("重复加入被拒(3003)", code == ErrorCode.DUPLICATE_JOIN)

# 10. 满员后再加入被拒
token3 = user_service.enter("乘客B", "保密")
code, _m, _d = trip_service.join_trip("乘客B", "保密", token3, trip_id)
check("队伍满员被拒(3001)", code == ErrorCode.TRIP_FULL)

# 11. 乘客退出
code, _m, _d = trip_service.leave_trip("乘客A", token2, trip_id)
check("乘客退出成功", code == ErrorCode.OK)

# 12. 状态流转
code, _m, _d = trip_service.change_status("队长", trip_id, TripStatus.DEPARTED)
check("队长标记出发", code == ErrorCode.OK)
code, _m, _d = trip_service.change_status("队长", trip_id, TripStatus.COMPLETED)
check("队长标记完成", code == ErrorCode.OK)

# 13. 性别校验：仅女生队伍拒绝男生
req_female = SimpleNamespace(
    teamName="女生拼车队", origin="滨海东门", destination="长乐南门", departAt="2099-01-01T09:00:00",
    seats=3, fee=None, originLat=25.8805227, originLng=119.5566502,
    destinationLat=25.9259051, destinationLng=119.4953332,
    gender="仅女生", remark=None,
)
code, _m, data_f = trip_service.create_trip("女队长", req_female)
check("创建仅女生队伍成功", code == ErrorCode.OK)
token_male = user_service.enter("男生", "男")
code, _m, _d = trip_service.join_trip("男生", "男", token_male, data_f["tripId"])
check("男生加入仅女生队伍被拒(3005)", code == ErrorCode.GENDER_MISMATCH)
token_female = user_service.enter("女生", "女")
code, _m, _d = trip_service.join_trip("女生", "女", token_female, data_f["tripId"])
check("女生加入仅女生队伍成功", code == ErrorCode.OK)

# 14. 帖子发布与浏览
code, _m, data = post_service.create_post("队长", SimpleNamespace(title="测试标题", content="测试内容", campusName="福州外语外贸学院滨海校区", topic="life"))
check("发帖成功", code == ErrorCode.OK)
items, total = post_service.list_posts(None, None, 1, 20)
check("帖子列表 ≥1 条", total >= 1)
post = post_service.get_post(data["postId"])
check("帖子详情可查", post is not None and post["title"] == "测试标题")

# 15. 评论发布与列表
code, _m, cdata = comment_service.create_comment("队长", data["postId"], "第一条评论")
check("评论发布成功", code == ErrorCode.OK)
code, _m, _d = comment_service.create_comment("队长", data["postId"], "")
check("空评论被拒(2004)", code == ErrorCode.POST_CONTENT_INVALID)
code, _m, _d = comment_service.create_comment("队长", data["postId"], "x" * 301)
check("超长评论被拒(2004)", code == ErrorCode.POST_CONTENT_INVALID)
comments = comment_service.list_comments(data["postId"])
check("评论列表 ≥1 条", len(comments) >= 1)

# 16. 点赞切换
result = like_service.toggle_like("队长", data["postId"])
check("首次点赞成功", result["liked"] is True and result["likeCount"] == 1)
result = like_service.toggle_like("队长", data["postId"])
check("再次点赞取消", result["liked"] is False and result["likeCount"] == 0)
result = like_service.toggle_like("乘客A", data["postId"])
check("不同用户独立点赞", result["liked"] is True and result["likeCount"] == 1)
status = like_service.get_like_status("队长", data["postId"])
check("点赞状态查询", status["liked"] is False and status["likeCount"] == 1)

failed = [n for n, c in results if not c]
print("\n" + ("ALL PASS ✅" if not failed else "FAILED: " + ", ".join(failed)))
sys.exit(0 if not failed else 1)