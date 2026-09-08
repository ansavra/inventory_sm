@echo off
chcp 65001 >nul
title SM Telegram Bot ^& Inventory Web Dashboard
cd /d "%~dp0"

echo ========================================================
echo   🚀 កំពុងដំណើរការប្រព័ន្ធ SM Inventory ^& Telegram Bot
echo ========================================================
echo.

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" run_system.py
) else (
    python run_system.py
)

pause
