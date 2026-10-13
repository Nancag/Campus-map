"""论坛分类功能验收测试。使用临时数据库。"""
import json, os, subprocess, sys, tempfile, time, urllib.request, urllib.error

BASE = "http://127.0.0.1:8000"
passed = 0
failed = 0

def report(name, ok, detail=""):
    global passed, failed
    if ok:
        passed += 1
        print(f"  PASS  {name}" + (f"  ({detail})" if detail else ""))
    else:
        failed += 1
        print(f"  FAIL  {name}" + (f"  ({detail})" if detail else ""))

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

def main():
    tmpdir = tempfile.mkdtemp()
    os.environ["CAMPUS_CARPOOL_DB"] = os.path.join(tmpdir, "test.db")
    os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

    proc = subprocess.Popen(
        [sys.executable, "-u", "-m", "app.main"],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        env={**os.environ},
    )
    time.sleep(3)
    if proc.poll() is not None:
        print("服务器启动失败:", proc.stdout.read().decode()[:300])
        sys.exit(1)

    try:
        run()
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()

    print(f"\n{'='*50}\n总计: {passed} PASS / {failed} FAIL")
    sys.exit(0 if failed == 0 else 1)

def run():
    r = api("POST", "/api/guest/enter", {"username": "tester", "gender": "保密"})
    token = r["data"]["token"]

    print("\n【验收1 发布校园生活 → 分类可见】")
    r = api("POST", "/api/posts", {"title": "校园停水通知", "topic": "life", "content": "明天停水"}, token=token)
    report("发布分类=life 成功", r["code"] == 0, r.get("message", ""))
    r = api("GET", "/api/posts?topic=life", token=token)
    items = r["data"]["items"]
    report("校园生活分类可见", any(p["title"] == "校园停水通知" for p in items), f"count={len(items)}")
    report("topic 保存为 life", items and all(p["topic"] == "life" for p in items), f"topics={[p['topic'] for p in items]}")

    print("\n【验收2 发布拼车交流 → 分类可见】")
    r = api("POST", "/api/posts", {"title": "周五晚上回福州拼车", "topic": "carpool", "content": "有位置"}, token=token)
    report("发布分类=carpool 成功", r["code"] == 0, r.get("message", ""))
    r = api("GET", "/api/posts?topic=carpool", token=token)
    items = r["data"]["items"]
    report("拼车交流分类可见", any(p["title"] == "周五晚上回福州拼车" for p in items), f"count={len(items)}")

    print("\n【验收3 全部两个分类都出现】")
    r = api("GET", "/api/posts", token=token)
    items = r["data"]["items"]
    report("全部含 life 帖子", any(p["topic"] == "life" for p in items))
    report("全部含 carpool 帖子", any(p["topic"] == "carpool" for p in items))
    report("总数=2", len(items) == 2, f"count={len(items)}")

    print("\n【验收4 论坛队伍自动进入拼车交流】")
    r = api("POST", "/api/trips", {
        "teamName": "分类测试队伍", "origin": "滨海北门", "destination": "万达",
        "originLat": 25.881, "originLng": 119.557,
        "destinationLat": 25.875, "destinationLng": 119.560,
        "departAt": "2099-01-01T08:00", "seats": 3, "gender": "不限",
    }, token=token)
    trip_id = r["data"]["tripId"]
    r = api("POST", "/api/posts", {"title": "队伍帖子", "topic": "carpool", "content": "拼车", "tripId": trip_id}, token=token)
    report("队伍帖发布成功", r["code"] == 0, r.get("message", ""))
    post_id = r["data"]["postId"]
    r = api("GET", f"/api/posts/{post_id}", token=token)
    report("队伍帖 topic=carpool", r["data"]["topic"] == "carpool", f"topic={r['data']['topic']}")
    report("队伍帖关联 tripId", r["data"]["tripId"] == trip_id)
    r = api("GET", "/api/posts?topic=carpool", token=token)
    items = r["data"]["items"]
    report("拼车交流含队伍帖", any(p.get("tripId") == trip_id for p in items))

if __name__ == "__main__":
    main()