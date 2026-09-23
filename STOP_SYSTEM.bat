@echo off
chcp 65001 >nul
title Stop SM Inventory System
cd /d "%~dp0"
echo ========================================================
echo   Stopping SM Inventory (Web + Bot + Tunnel) ...
echo ========================================================
if exist ".sm_pids" (
    for /f "usebackq" %%p in (".sm_pids") do taskkill /F /T /PID %%p >nul 2>&1
    erase ".sm_pids" >nul 2>&1
)
rem បិទអ្វីដែលនៅសល់លើ port 8000 (ករណី .sm_pids ចាស់ ឬបាត់)
for /f "tokens=5" %%p in ('netstat -ano ^| findstr ":8000" ^| findstr "LISTENING"') do taskkill /F /T /PID %%p >nul 2>&1
taskkill /F /IM cloudflared.exe >nul 2>&1
echo.
echo   OK - បានបិទប្រព័ន្ធ SM Inventory រួចរាល់។
timeout /t 3 >nul
