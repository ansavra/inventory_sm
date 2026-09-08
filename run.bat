@echo off
chcp 65001 >nul
title SM Local Server - Inventory Web ^& Telegram Bot
cd /d "%~dp0"

echo ========================================================
echo   🚀 កំពុងដំណើរការប្រព័ន្ធ SM Inventory ក្នុង LOCAL SERVER
echo ========================================================
echo.

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" run_local.py
) else (
    python run_local.py
)

pause
