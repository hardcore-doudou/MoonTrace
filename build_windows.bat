@echo off
setlocal EnableExtensions
cd /d "%~dp0"
set "RELEASE_VERSION="
set /p RELEASE_VERSION=<VERSION
if not defined RELEASE_VERSION (
    echo VERSION is empty.
    exit /b 1
)
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
if not exist "dist\MoonTrace\MoonTrace.exe" exit /b 1
type nul > "dist\MoonTrace\moontrace.portable"
copy /y "PORTABLE_README.txt" "dist\MoonTrace\README.txt" >nul
if errorlevel 1 exit /b 1
powershell.exe -NoProfile -ExecutionPolicy Bypass -Command ^
  "$ErrorActionPreference='Stop'; $version=$env:RELEASE_VERSION; $zip=Join-Path (Get-Location) ('dist\MoonTrace-'+$version+'-Windows-Portable.zip'); if(Test-Path $zip){Remove-Item $zip -Force}; Compress-Archive -Path 'dist\MoonTrace' -DestinationPath $zip -CompressionLevel Optimal; $archive=[System.IO.Compression.ZipFile]::OpenRead($zip); try { if(-not ($archive.Entries.FullName -contains 'MoonTrace/MoonTrace.exe' -or $archive.Entries.FullName -contains 'MoonTrace\MoonTrace.exe')) { throw 'ZIP is missing MoonTrace.exe' } } finally { $archive.Dispose() }; Write-Host ('Portable ZIP: '+$zip)"
if errorlevel 1 exit /b 1
echo Built dist\MoonTrace\MoonTrace.exe
echo Windows portable ZIP ready.
