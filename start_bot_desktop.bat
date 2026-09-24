@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo Run setup.bat first.
    pause
    exit /b 1
)
set "MOONTRACE_DATA_DIR=%LOCALAPPDATA%\MoonTrace"
".venv\Scripts\python.exe" -m telegram_bot.bot
if errorlevel 1 pause
