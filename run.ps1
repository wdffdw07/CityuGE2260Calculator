# PowerShell启动脚本
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "2260 订单驱动回测系统" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

Set-Location $PSScriptRoot
$env:PYTHONIOENCODING = "utf-8"

uv run python main.py

Read-Host "按任意键退出..."
