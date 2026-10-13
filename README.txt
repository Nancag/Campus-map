Campus map 一键启动说明
====================================

步骤：
1. 解压项目压缩包
2. 双击 start.bat
3. 等待服务器启动
4. 浏览器自动打开：http://127.0.0.1:8000/map_amap.html

如果浏览器没有自动打开，请手动访问：
  http://127.0.0.1:8000/map_amap.html   （拼车地图）
  http://127.0.0.1:8000/forum.html      （论坛）
  http://127.0.0.1:8000/                （首页）

让同局域网的人访问：
  http://你的IP:8000/map_amap.html
  （服务器默认绑定 0.0.0.0:8000，同一网络内可直接访问）

停止服务器：
  在命令窗口按 Ctrl+C

环境要求：
  - Windows 7 及以上
  - Python 3.9 或更高版本（首次使用需安装：https://www.python.org/downloads/）
    安装时务必勾选 "Add Python to PATH"
  - 本项目零第三方依赖，安装 Python 后即可运行

常见问题：
  - 提示"未检测到 Python"：请安装 Python 并勾选 Add Python to PATH，然后重新双击 start.bat
  - 提示"端口被占用"：请关闭占用 8000 端口的程序后重试
  - 地图白屏：请确认电脑能正常联网（高德地图 JS 从外网加载）