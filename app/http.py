"""HTTP 服务：基于标准库 http.server 的路由分发、会话鉴权、静态托管。"""
"""Campus map Python HTTP 服务器。"""

import json
import mimetypes
import os
import re
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from app.api import campus_boundaries, campuses, guest, pois, posts, trips
from app.api import campus_gates
from app.api.deps import parse_bearer
from app.config import STATIC_DIR
from app.models.schemas import AppError, ErrorCode, err
from app.services.user_service import authenticate

# 路由表：(路径正则, 允许的方法集合, 处理函数)
ROUTES = [
    (r"/api/guest/enter", {"POST"}, guest.enter),
    (r"/api/campuses", {"GET"}, campuses.list_campuses),
    (r"/api/campus-boundaries", {"GET"}, campus_boundaries.list_boundaries),
    (r"/api/pois", {"GET"}, pois.list_pois),
    (r"/api/trips", {"POST"}, trips.create_trip),
    (r"/api/trips", {"GET"}, trips.list_trips),
    (r"/api/my-teams", {"GET"}, trips.my_teams),
    (r"/api/trips/(?P<id>\w+)", {"GET"}, trips.get_trip),
    (r"/api/trips/(?P<id>\w+)", {"DELETE"}, trips.delete_trip),
    (r"/api/trips/(?P<id>\w+)/join", {"POST"}, trips.join_trip),
    (r"/api/trips/(?P<id>\w+)/leave", {"POST"}, trips.leave_trip),
    (r"/api/trips/(?P<id>\w+)/depart", {"POST"}, trips.depart),
    (r"/api/trips/(?P<id>\w+)/complete", {"POST"}, trips.complete),
    (r"/api/trips/(?P<id>\w+)/cancel", {"POST"}, trips.cancel),
    (r"/api/trips/(?P<id>\w+)/edit", {"POST"}, trips.edit_trip),
    (r"/api/trips/(?P<id>\w+)/kick", {"POST"}, trips.kick_member),
    (r"/api/trips/(?P<id>\w+)/dissolve", {"POST"}, trips.dissolve_trip),
    (r"/api/trips/(?P<id>\w+)/members", {"GET"}, trips.list_members),
    (r"/api/posts", {"POST"}, posts.create_post),
    (r"/api/posts", {"GET"}, posts.list_posts),
    (r"/api/posts/(?P<id>\w+)", {"GET"}, posts.get_post),
    (r"/api/posts/(?P<id>\w+)", {"DELETE"}, posts.delete_post),
    (r"/api/posts/(?P<id>\w+)/comments", {"POST"}, posts.create_comment),
    (r"/api/posts/(?P<id>\w+)/comments", {"GET"}, posts.list_comments),
    (r"/api/posts/(?P<id>\w+)/like", {"POST"}, posts.toggle_like),
    (r"/api/campus-gates", {"GET"}, campus_gates.list_gates),
    (r"/api/campus-gates", {"POST"}, campus_gates.save_gate),
]


class AppHandler(BaseHTTPRequestHandler):
    server_version = "CampusMap/0.1"

    # ---- 辅助方法 ----
    def _send_json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def get_session(self):
        auth = self.headers.get("Authorization", "")
        token = parse_bearer(auth)
        username, gender = authenticate(token) if token else (None, None)
        if username is None:
            raise AppError(401, ErrorCode.UNAUTHORIZED, "未登录或会话已失效")
        return token, username, gender

    def q(self, key, default=None):
        vals = self.query.get(key)
        return vals[0] if vals else default

    def int_q(self, key, default=0):
        try:
            return int(self.q(key, default))
        except (TypeError, ValueError):
            return default

    def _read_json_body(self) -> dict:
        length = int(self.headers.get("Content-Length", 0) or 0)
        raw = self.rfile.read(length) if length else b""
        if not raw:
            return {}
        try:
            data = json.loads(raw.decode("utf-8"))
            return data if isinstance(data, dict) else {}
        except (ValueError, UnicodeDecodeError):
            raise AppError(400, 400, "请求体不是合法 JSON")

    # ---- 路由与静态 ----
    def _route(self):
        parsed = urlparse(self.path)
        path = parsed.path
        self.query = parse_qs(parsed.query)
        for regex, methods, fn in ROUTES:
            if self.command not in methods:
                continue
            m = re.fullmatch(regex, path)
            if m:
                return fn, m.groupdict()
        return None, {}

    def _serve_static(self) -> None:
        base = os.path.realpath(STATIC_DIR)
        rel = self.path.lstrip("/")
        target = os.path.realpath(os.path.join(base, rel))
        if target != base and not target.startswith(base + os.sep):
            raise AppError(404, ErrorCode.NOT_FOUND, "未找到")
        if os.path.isdir(target):
            target = os.path.join(target, "index.html")
        if not os.path.isfile(target):
            raise AppError(404, ErrorCode.NOT_FOUND, "未找到")

        ctype = mimetypes.guess_type(target)[0] or "application/octet-stream"
        with open(target, "rb") as f:
            data = f.read()
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _handle(self) -> None:
        try:
            fn, path_params = self._route()
            if fn is not None:
                body = self._read_json_body() if self.command == "POST" else {}
                result = fn(self, body, path_params)
                self._send_json(200, result)
            elif self.command in ("GET", "HEAD"):
                self._serve_static()
            else:
                raise AppError(404, ErrorCode.NOT_FOUND, "未找到")
        except AppError as e:
            self._send_json(e.status, err(e.code, e.message))
        except Exception:
            self._send_json(500, err(500, "服务器内部错误"))

    def do_GET(self):
        self._handle()

    def do_HEAD(self):
        self._handle()

    def do_POST(self):
        self._handle()

    def do_DELETE(self):
        self._handle()

    def log_message(self, format, *args):
        pass  # 静默访问日志


def _auto_open_browser(url: str) -> None:
    """延迟自动打开默认浏览器（后台线程执行，不阻塞服务器）。"""
    try:
        import webbrowser
        webbrowser.open(url)
    except Exception as e:  # noqa: BLE001
        print(f"[提示] 自动打开浏览器失败：{e}", flush=True)


def run_server(host: str = "0.0.0.0", port: int = 8000, auto_open_browser: bool = False) -> None:
    try:
        server = ThreadingHTTPServer((host, port), AppHandler)
    except OSError as e:
        print(f"无法启动服务器：端口 {port} 可能已被占用。\n请先终止占用该端口的进程，再重试。\n原始错误：{e}", flush=True)
        return
    print(f"Campus map 已启动：http://127.0.0.1:{port}", flush=True)
    if auto_open_browser:
        url = f"http://127.0.0.1:{port}/map_amap.html"
        threading.Timer(1.5, _auto_open_browser, args=(url,)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n服务器已停止。", flush=True)
    finally:
        server.server_close()