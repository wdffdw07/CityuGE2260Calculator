@echo off
REM 数据库清理工具 - Windows批处理快捷方式
echo ========================================
echo 数据库清理工具
echo ========================================
echo.

cd /d %~dp0
uv run python clear_database.py

pause
