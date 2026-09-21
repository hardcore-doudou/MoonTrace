@echo off
title MoonTrace Launcher
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo.
    echo [MoonTrace] .venv was not found.
    echo Run setup.bat first.
    echo.
    pause
    exit /b 1
)

echo Starting MoonTrace Web...
start "MoonTrace Web" "%~dp0start.bat"

if exist ".env" (
    echo Starting MoonTrace Telegram Bot...
    start "MoonTrace Telegram" "%~dp0start_bot.bat"
) else (
    echo Telegram config .env not found. Bot was skipped.
)

exit /b 0
