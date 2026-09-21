from pathlib import Path
import shutil

from config import BASE_DIR


FFMPEG_BIN_DIR = BASE_DIR / "tools" / "ffmpeg" / "bin"
FFMPEG_EXE = FFMPEG_BIN_DIR / "ffmpeg.exe"
FFPROBE_EXE = FFMPEG_BIN_DIR / "ffprobe.exe"


def bundled_ffmpeg_available() -> bool:
    """Return whether setup.bat installed the project-local FFmpeg tools."""
    return FFMPEG_EXE.is_file() and FFPROBE_EXE.is_file()


def find_ffmpeg() -> Path | None:
    """Prefer MoonTrace's own FFmpeg, then fall back to the system PATH."""
    if bundled_ffmpeg_available():
        return FFMPEG_EXE

    executable = shutil.which("ffmpeg")
    return Path(executable) if executable else None


def ffmpeg_available() -> bool:
    return find_ffmpeg() is not None


def apply_ffmpeg_options(options: dict) -> None:
    """Point yt-dlp at the bundled FFmpeg directory when it is available."""
    if bundled_ffmpeg_available():
        options["ffmpeg_location"] = str(FFMPEG_BIN_DIR)
