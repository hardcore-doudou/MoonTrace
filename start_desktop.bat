@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo Run setup.bat first.
    pause
    exit /b 1
)
".venv\Scripts\python.exe" -c "import webview" >nul 2>&1
if errorlevel 1 (
    echo Installing desktop dependencies...
    ".venv\Scripts\python.exe" -m pip install -r requirements-desktop.txt
    if errorlevel 1 (
        pause
        exit /b 1
    )
)
".venv\Scripts\python.exe" desktop.py
if errorlevel 1 pause
