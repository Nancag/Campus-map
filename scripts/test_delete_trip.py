"""车队删除功能测试。直接调用 service 层，使用临时数据库。"""
import os
import sys
import tempfile
from types import SimpleNamespace

tmpdir = tempfile.mkdtemp()
os.environ["CAMPUS_CARPOOL_DB"] = os.path.join(tmpdir, "test.db")
os.environ["CAMPUS_ADMIN_USERNAMES"] = "admin"

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from app.models.db import init_db
from app.models.schemas import ErrorCode
from app.services import trip_service

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


print("【车队删除功能测试】")

req = SimpleNamespace(
    teamName="测试车队A", origin="北门", destination="福州火车站",
    departAt="2099-12-31T08:00", seats=4, fee=None,
    originLat=25.9, originLng=119.3, destinationLat=26.0, destinationLng=119.6,
    gender="不限", remark=None,
)

# 1. 创建者删除自己的车队
code, msg, data = trip_service.create_trip("alice", req, "保密")
check("alice 创建车队成功", code == ErrorCode.OK, msg)
trip_id_1 = data["tripId"]

code, msg, data = trip_service.delete_trip("alice", trip_id_1)
check("创建者删除自己车队成功", code == ErrorCode.OK, msg)

trip = trip_service.get_trip(trip_id_1)
check("删除后 get_trip 返回 None", trip is None, f"trip={trip}")

items, total = trip_service.list_trips(None, None, None, None, 1, 20)
check("删除后列表不含该车队", not any(t["tripId"] == trip_id_1 for t in items), f"total={total}")

# 2. 非创建者删除被拒
code, msg, data = trip_service.create_trip("bob", req, "保密")
check("bob 创建车队成功", code == ErrorCode.OK, msg)
trip_id_2 = data["tripId"]

code, msg, data = trip_service.delete_trip("alice", trip_id_2)
check("非创建者删除被拒(FORBIDDEN)", code == ErrorCode.FORBIDDEN, f"code={code} msg={msg}")

trip = trip_service.get_trip(trip_id_2)
check("被拒后车队仍存在", trip is not None, f"trip={trip}")

# 3. 管理员删除任意车队
code, msg, data = trip_service.delete_trip("admin", trip_id_2)
check("管理员删除成功", code == ErrorCode.OK, msg)

trip = trip_service.get_trip(trip_id_2)
check("管理员删除后车队不存在", trip is None, f"trip={trip}")

# 4. 删除不存在的车队
code, msg, data = trip_service.delete_trip("alice", "t_nonexistent")
check("删除不存在的车队返回 NOT_FOUND", code == ErrorCode.NOT_FOUND, f"code={code} msg={msg}")

# 5. 删除后 my_teams 不含已删除车队
teams = trip_service.get_trips_by_leader("alice")
check("alice my_teams 不含已删除车队", not any(t["tripId"] == trip_id_1 for t in teams), f"teams={len(teams)}")

print(f"\n{'='*50}")
print(f"总计: {passed} PASS / {failed} FAIL")
print(f"{'='*50}")
sys.exit(0 if failed == 0 else 1)