@echo off
chcp 65001 >nul
title Campus map 校园拼车平台
cd /d "%~dp0"

echo ============================================
echo   Campus map 校园拼车平台 一键启动
echo ============================================
echo.

REM ---------- 检测 Python ----------
set "PYCMD="
where py >nul 2>nul && set "PYCMD=py"
if not defined PYCMD (
    where python >nul 2>nul && set "PYCMD=python"
)
if not defined PYCMD (
    echo [错误] 未检测到 Python。
    echo 请先安装 Python 3.9 或更高版本，安装时勾选 "Add Python to PATH"。
    echo 下载地址：https://www.python.org/downloads/
    echo.
    pause
    exit /b 1
)

echo [1/3] 检查 Python 环境...
%PYCMD% --version
if errorlevel 1 (
    echo [错误] 无法执行 Python，请重新安装后重试。
    echo.
    pause
    exit /b 1
)
%PYCMD% -c "import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)" 2>nul
if errorlevel 1 (
    echo [错误] 需要 Python 3.9 或更高版本，当前版本过低。
    echo 请升级：https://www.python.org/downloads/
    echo.
    pause
    exit /b 1
)

REM ---------- 安装依赖 ----------
echo.
echo [2/3] 检查依赖（本项目零第三方依赖，如无网络可自动跳过）...
%PYCMD% -m pip install -r requirements.txt >nul 2>nul

REM ---------- 启动服务器并自动打开浏览器 ----------
echo.
echo [3/3] 启动服务器...
echo 服务器地址：http://127.0.0.1:8000
echo 浏览器将自动打开，按 Ctrl+C 停止服务器。
echo.
set CAMPUS_AUTO_OPEN_BROWSER=1
%PYCMD% -m app.main

echo.
echo 服务器已停止。
pause