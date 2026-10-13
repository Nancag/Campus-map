"""Campus map 核心闭环端到端验收测试。

使用临时数据库，不污染正式 DB。
启动子进程服务器，通过 HTTP API 完成全部 11 个测试场景。
"""
import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.request
import urllib.error

BASE = "http://127.0.0.1:8000"

passed = 0
failed = 0
results = []


def report(name, ok, detail=""):
    global passed, failed
    status = "PASS" if ok else "FAIL"
    if ok:
        passed += 1
    else:
        failed += 1
    results.append((name, status, detail))
    print(f"  {status}  {name}" + (f"  ({detail})" if detail else ""))


def api(method, path, body=None, token=None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = "Bearer " + token
    data = json.dumps(body).encode("utf-8") if body else None
    req = urllib.request.Request(BASE + path, data=data, headers=headers, method=method)
    try:
        resp = urllib.request.urlopen(req, timeout=5)
        return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return json.loads(e.read().decode("utf-8"))
    except Exception as e:
        return {"code": -1, "message": str(e)}


def enter(username, gender):
    r = api("POST", "/api/guest/enter", {"username": username, "gender": gender})
    assert r["code"] == 0, f"登录失败: {r}"
    return r["data"]["token"]


FUTURE_TIME = "2099-12-31T23:59"


def main():
    tmpdir = tempfile.mkdtemp()
    db_path = os.path.join(tmpdir, "test.db")
    os.environ["CAMPUS_CARPOOL_DB"] = db_path
    os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

    proc = subprocess.Popen(
        [sys.executable, "-u", "-m", "app.main"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        env={**os.environ},
    )
    time.sleep(3)
    if proc.poll() is not None:
        out = proc.stdout.read().decode("utf-8", errors="replace")
        print(f"服务器启动失败:\n{out}")
        sys.exit(1)

    try:
        run_tests()
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()

    print(f"\n{'='*60}")
    print(f"总计: {passed} PASS / {failed} FAIL")
    print(f"{'='*60}")
    sys.exit(0 if failed == 0 else 1)


def run_tests():
    ta = enter("userA", "女")
    tb = enter("userB", "男")
    tc = enter("userC", "女")

    print("\n【测试1 创建队伍】")
    r = api("POST", "/api/trips", {
        "teamName": "滨海测试队",
        "origin": "福州外语外贸学院滨海校区 · 北门",
        "destination": "万达广场",
        "originLat": 25.881, "originLng": 119.557,
        "destinationLat": 25.875, "destinationLng": 119.560,
        "departAt": FUTURE_TIME,
        "seats": 5,
        "gender": "仅女生",
        "remark": "测试队伍",
    }, token=ta)
    report("A创建队伍成功", r["code"] == 0, r.get("message", ""))
    trip_id = r["data"]["tripId"] if r["code"] == 0 else None

    r = api("GET", f"/api/trips/{trip_id}", token=ta)
    report("A自动成为队长", r["data"]["leaderName"] == "userA", f"leader={r['data']['leaderName']}")
    report("当前人数1/5", r["data"]["currentSeats"] == 1 and r["data"]["maxSeats"] == 5, f"{r['data']['currentSeats']}/{r['data']['maxSeats']}")

    r = api("GET", f"/api/trips/{trip_id}/members", token=ta)
    report("成员表含队长", any(m["username"] == "userA" for m in r["data"]["members"]), f"members={len(r['data']['members'])}")

    print("\n【测试2 性别限制】")
    r = api("POST", f"/api/trips/{trip_id}/join", token=tb)
    report("B(男)加入被拒", r["code"] == 3005, f"code={r['code']} msg={r['message']}")

    print("\n【测试3 正常加入】")
    r = api("POST", f"/api/trips/{trip_id}/join", token=tc)
    report("C(女)加入成功", r["code"] == 0, r.get("message", ""))
    r = api("GET", f"/api/trips/{trip_id}", token=tc)
    report("人数2/5", r["data"]["currentSeats"] == 2, f"{r['data']['currentSeats']}/5")

    print("\n【测试4 队长管理】")
    r = api("POST", f"/api/trips/{trip_id}/edit", {"teamName": "滨海周末拼车队"}, token=ta)
    report("A修改队名成功", r["code"] == 0, r.get("message", ""))
    r = api("GET", f"/api/trips/{trip_id}", token=ta)
    report("队名已更新", r["data"]["teamName"] == "滨海周末拼车队", f"teamName={r['data']['teamName']}")

    print("\n【测试5 普通成员权限】")
    r = api("POST", f"/api/trips/{trip_id}/edit", {"teamName": "被篡改的队名"}, token=tc)
    report("C修改队名被拒", r["code"] == 3006, f"code={r['code']} msg={r['message']}")

    print("\n【测试6 队长踢人】")
    r = api("POST", f"/api/trips/{trip_id}/kick", {"username": "userC"}, token=ta)
    report("A踢出C成功", r["code"] == 0, r.get("message", ""))
    r = api("GET", f"/api/trips/{trip_id}", token=ta)
    report("人数回到1/5", r["data"]["currentSeats"] == 1, f"{r['data']['currentSeats']}/5")

    print("\n【测试7 校门规则】")
    r = api("POST", "/api/trips", {
        "teamName": "非法队伍",
        "origin": "普通商店", "destination": "普通餐厅",
        "originLat": 25.875, "originLng": 119.560,
        "destinationLat": 25.880, "destinationLng": 119.565,
        "departAt": FUTURE_TIME, "seats": 3, "gender": "不限",
    }, token=ta)
    report("非校门→非校门被拒", r["code"] == 2005, f"code={r['code']} msg={r['message']}")

    r = api("POST", "/api/trips", {
        "teamName": "合法队伍1",
        "origin": "普通商店", "destination": "滨海南门",
        "originLat": 25.875, "originLng": 119.560,
        "destinationLat": 25.879, "destinationLng": 119.555,
        "departAt": FUTURE_TIME, "seats": 3, "gender": "不限",
    }, token=ta)
    report("普通→南门允许", r["code"] == 0, r.get("message", ""))

    r = api("POST", "/api/trips", {
        "teamName": "合法队伍2",
        "origin": "滨海北门", "destination": "普通商店",
        "originLat": 25.881, "originLng": 119.557,
        "destinationLat": 25.875, "destinationLng": 119.560,
        "departAt": FUTURE_TIME, "seats": 3, "gender": "不限",
    }, token=ta)
    report("北门→普通允许", r["code"] == 0, r.get("message", ""))

    print("\n【测试8 论坛发布】")
    r = api("GET", "/api/my-teams", token=ta)
    report("A获取队长队伍列表", r["code"] == 0 and len(r["data"]["items"]) >= 1, f"teams={r['data']['total']}")

    r = api("POST", "/api/posts", {
        "title": "滨海周末拼车走起",
        "topic": "carpool",
        "content": "有人一起拼车吗？",
        "tripId": trip_id,
    }, token=ta)
    report("A发布队伍帖成功", r["code"] == 0, r.get("message", ""))
    post_id = r["data"]["postId"] if r["code"] == 0 else None

    r = api("GET", "/api/posts", token=ta)
    team_posts = [p for p in r["data"]["items"] if p.get("tripId")]
    report("论坛列表含队伍帖", len(team_posts) >= 1, f"team_posts={len(team_posts)}")

    r = api("GET", f"/api/posts/{post_id}", token=ta)
    report("帖子关联真实trip_id", r["data"].get("tripId") == trip_id, f"tripId={r['data'].get('tripId')}")
    report("帖子含trip详情", r["data"].get("trip") is not None, f"trip={'有' if r['data'].get('trip') else '无'}")

    print("\n【测试9 论坛性别限制】")
    r = api("POST", f"/api/trips/{trip_id}/join", token=tb)
    report("B(男)论坛加入被拒", r["code"] == 3005, f"code={r['code']} msg={r['message']}")

    print("\n【测试10 论坛正常加入】")
    r = api("POST", f"/api/trips/{trip_id}/join", token=tc)
    report("C(女)论坛加入成功", r["code"] == 0, r.get("message", ""))
    r = api("GET", f"/api/trips/{trip_id}", token=tc)
    report("论坛加入后人数2/5", r["data"]["currentSeats"] == 2, f"{r['data']['currentSeats']}/5")
    r = api("GET", f"/api/posts/{post_id}", token=tc)
    trip_info = r["data"].get("trip", {})
    report("论坛trip详情同步人数", trip_info.get("currentSeats") == 2, f"forum_seats={trip_info.get('currentSeats')}")

    print("\n【测试11 解散队伍】")
    r = api("POST", f"/api/trips/{trip_id}/dissolve", token=ta)
    report("A解散队伍成功", r["code"] == 0, r.get("message", ""))
    r = api("GET", f"/api/trips/{trip_id}", token=ta)
    report("队伍状态已取消", r["data"]["status"] == "已取消", f"status={r['data']['status']}")
    r = api("POST", f"/api/trips/{trip_id}/join", token=tb)
    report("解散后加入被拒", r["code"] != 0, f"code={r['code']} msg={r['message']}")


if __name__ == "__main__":
    main()