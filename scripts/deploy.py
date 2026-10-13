"""环境检查与启动编排（零第三方依赖）。用法：python scripts/deploy.py"""
import os
import sys

MIN_PY = (3, 9)

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)


def main() -> None:
    base = ROOT_DIR
    os.chdir(base)

    print("=" * 50)
    print("Campus map · 环境检查")
    print(f"Python: {sys.version.split()[0]}")
    if sys.version_info < MIN_PY:
        sys.exit("错误：需要 Python 3.9+")
    print("无第三方依赖，检查通过 ✅")
    print("=" * 50)

    from app.http import run_server
    from app.models.db import init_db

    init_db()
    auto_open = os.environ.get("CAMPUS_AUTO_OPEN_BROWSER") == "1"
    run_server(auto_open_browser=auto_open)


if __name__ == "__main__":
    main()