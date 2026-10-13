"""应用入口：初始化数据库并启动 HTTP 服务。"""
import os
import sys

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from app.http import run_server  # noqa: E402
from app.models.db import init_db  # noqa: E402

if __name__ == "__main__":
    init_db()
    auto_open = os.environ.get("CAMPUS_AUTO_OPEN_BROWSER") == "1"
    run_server(auto_open_browser=auto_open)