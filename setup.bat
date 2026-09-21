@echo off
setlocal EnableExtensions EnableDelayedExpansion
title MoonTrace Setup
cd /d "%~dp0"

echo.
echo ========================================
echo   MoonTrace Setup
echo ========================================
echo.

if exist ".venv\Scripts\python.exe" (
    echo Existing .venv found.
) else (
    echo Checking Python...
    py -3.13 --version >nul 2>&1
    if not errorlevel 1 (
        set "PY_LAUNCHER=py -3.13"
    ) else (
        py -3 --version >nul 2>&1
        if errorlevel 1 (
            echo.
            echo Python 3 was not found.
            echo Install Python 3.10 or newer, then run setup.bat again.
            echo https://www.python.org/downloads/
            pause
            exit /b 1
        )
        set "PY_LAUNCHER=py -3"
    )

    echo Creating Python virtual environment...
    !PY_LAUNCHER! -m venv .venv

    if errorlevel 1 (
        echo.
        echo Failed to create .venv.
        echo Check that Python 3.10 or newer is installed.
        pause
        exit /b 1
    )
)

".venv\Scripts\python.exe" -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)"
if errorlevel 1 (
    echo.
    echo MoonTrace requires Python 3.10 or newer.
    echo Delete .venv after installing a newer Python, then run setup.bat again.
    pause
    exit /b 1
)

echo.
echo Updating pip...
".venv\Scripts\python.exe" -m pip install --upgrade pip

if errorlevel 1 (
    echo.
    echo pip update failed.
    pause
    exit /b 1
)

echo.
echo Installing project dependencies...
".venv\Scripts\python.exe" -m pip install -r requirements.txt

if errorlevel 1 (
    echo.
    echo Dependency installation failed.
    pause
    exit /b 1
)

echo.
echo Checking yt-dlp...
".venv\Scripts\python.exe" -c "import yt_dlp; print('yt-dlp ' + yt_dlp.version.__version__)"

if errorlevel 1 (
    echo.
    echo yt-dlp verification failed.
    pause
    exit /b 1
)

echo.
echo Checking FFmpeg...

if exist "tools\ffmpeg\bin\ffmpeg.exe" if exist "tools\ffmpeg\bin\ffprobe.exe" (
    echo Project-local FFmpeg is ready.
    goto :ffmpeg_ready
)

where ffmpeg >nul 2>&1
if not errorlevel 1 (
    where ffprobe >nul 2>&1
    if not errorlevel 1 (
        echo System FFmpeg is ready.
        goto :ffmpeg_ready
    )
)

echo FFmpeg was not found. Downloading it for MoonTrace...

if not exist "tools" mkdir "tools"

powershell.exe -NoProfile -ExecutionPolicy Bypass -Command ^
  "$ErrorActionPreference = 'Stop';" ^
  "$zip = Join-Path $env:TEMP 'MoonTrace-ffmpeg.zip';" ^
  "$extract = Join-Path $env:TEMP 'MoonTrace-ffmpeg-extract';" ^
  "$urls = @('https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip', 'https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip');" ^
  "Remove-Item $zip -Force -ErrorAction SilentlyContinue;" ^
  "Remove-Item $extract -Recurse -Force -ErrorAction SilentlyContinue;" ^
  "$downloaded = $false;" ^
  "foreach ($url in $urls) { try { Write-Host ('Downloading: ' + $url); Invoke-WebRequest -Uri $url -OutFile $zip -UseBasicParsing; $downloaded = $true; break } catch { Write-Host ('Download failed: ' + $_.Exception.Message) } };" ^
  "if (-not $downloaded) { throw 'All FFmpeg download sources failed.' };" ^
  "Expand-Archive -Path $zip -DestinationPath $extract -Force;" ^
  "$ffmpeg = Get-ChildItem $extract -Filter ffmpeg.exe -Recurse | Select-Object -First 1;" ^
  "$ffprobe = Get-ChildItem $extract -Filter ffprobe.exe -Recurse | Select-Object -First 1;" ^
  "if (-not $ffmpeg -or -not $ffprobe) { throw 'The downloaded archive does not contain FFmpeg.' };" ^
  "$target = Join-Path (Get-Location) 'tools\ffmpeg\bin';" ^
  "New-Item -ItemType Directory -Path $target -Force | Out-Null;" ^
  "Copy-Item $ffmpeg.FullName (Join-Path $target 'ffmpeg.exe') -Force;" ^
  "Copy-Item $ffprobe.FullName (Join-Path $target 'ffprobe.exe') -Force;" ^
  "Remove-Item $zip -Force -ErrorAction SilentlyContinue;" ^
  "Remove-Item $extract -Recurse -Force -ErrorAction SilentlyContinue;"

if errorlevel 1 (
    echo.
    echo FFmpeg download or extraction failed.
    echo Check your network connection, then run setup.bat again.
    pause
    exit /b 1
)

if not exist "tools\ffmpeg\bin\ffmpeg.exe" (
    echo.
    echo FFmpeg installation failed: ffmpeg.exe is missing.
    pause
    exit /b 1
)

if not exist "tools\ffmpeg\bin\ffprobe.exe" (
    echo.
    echo FFmpeg installation failed: ffprobe.exe is missing.
    pause
    exit /b 1
)

echo Project-local FFmpeg installed successfully.

:ffmpeg_ready
echo.
echo Setup complete.
echo You can now run start.bat.
echo.
pause

