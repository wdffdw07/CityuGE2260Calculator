@echo off
REM 启动脚本 - 使用uv运行以确保环境正确
echo ========================================
echo 2260 订单驱动回测系统
echo ========================================
echo.

cd /d %~dp0
uv run python main.py

pause
