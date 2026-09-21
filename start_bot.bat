@echo off
title MoonTrace Telegram Bot
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo.
    echo [MoonTrace] .venv was not found.
    echo Run setup.bat first.
    echo.
    pause
    exit /b 1
)

if exist "tools\ffmpeg\bin\ffmpeg.exe" if exist "tools\ffmpeg\bin\ffprobe.exe" goto :ffmpeg_ready

where ffmpeg >nul 2>&1
if errorlevel 1 goto :ffmpeg_missing
where ffprobe >nul 2>&1
if errorlevel 1 goto :ffmpeg_missing
goto :ffmpeg_ready

:ffmpeg_missing
echo.
echo [MoonTrace] FFmpeg was not found.
echo Run setup.bat to install it automatically.
echo.
pause
exit /b 1

:ffmpeg_ready
if not exist ".env" (
    echo.
    echo [MoonTrace] .env was not found.
    echo Run telegram_setup.bat first.
    echo.
    pause
    exit /b 1
)

echo.
echo ========================================
echo   MoonTrace Telegram Bot
echo ========================================
echo.
echo Close this window or press Ctrl+C to stop.
echo.

".venv\Scripts\python.exe" -m telegram_bot.bot

echo.
echo MoonTrace Telegram Bot stopped.
pause

