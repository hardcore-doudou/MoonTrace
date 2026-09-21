@echo off
title MoonTrace Web
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
echo.
echo ========================================
echo   MoonTrace Web
echo   http://127.0.0.1:8000
echo ========================================
echo.
echo Close this window or press Ctrl+C to stop.
echo.

start "" "http://127.0.0.1:8000"
".venv\Scripts\python.exe" -m fastapi dev app.py

echo.
echo MoonTrace Web stopped.
pause

