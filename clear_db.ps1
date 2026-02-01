# 数据库清理工具 - PowerShell快捷方式
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "数据库清理工具" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

Set-Location $PSScriptRoot
$env:PYTHONIOENCODING = "utf-8"

uv run python clear_database.py

Read-Host "按任意键退出..."
