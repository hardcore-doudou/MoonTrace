@echo off
title MoonTrace Telegram Setup
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo.
    echo [MoonTrace] .venv was not found.
    echo Run setup.bat first.
    echo.
    pause
    exit /b 1
)

".venv\Scripts\python.exe" -m telegram_bot.configure

echo.
pause
