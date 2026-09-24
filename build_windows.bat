@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo Run setup.bat first.
    exit /b 1
)
if not exist "tools\ffmpeg\bin\ffmpeg.exe" (
    echo Run setup.bat to install FFmpeg before building.
    exit /b 1
)
if not exist "tools\ffmpeg\bin\ffprobe.exe" (
    echo Missing ffprobe.exe. Run setup.bat first.
    exit /b 1
)
".venv\Scripts\python.exe" -m pip install -r requirements-build.txt
if errorlevel 1 exit /b 1
".venv\Scripts\python.exe" -m PyInstaller --noconfirm --clean --onedir --windowed --name MoonTrace ^
  --add-data "static:static" ^
  --add-binary "tools\ffmpeg\bin\ffmpeg.exe:tools\ffmpeg\bin" ^
  --add-binary "tools\ffmpeg\bin\ffprobe.exe:tools\ffmpeg\bin" ^
  --collect-all webview ^
  --collect-submodules yt_dlp ^
  --collect-submodules uvicorn ^
  desktop.py
if errorlevel 1 exit /b 1
echo Built dist\MoonTrace\MoonTrace.exe
echo ZIP the entire dist\MoonTrace folder for a portable release.
