import yt_dlp

from core.cookies import apply_cookie_options
from core.ffmpeg import apply_ffmpeg_options
from core.parser import pick_first_entry, safe_filename, unique_path
from core.tasks import update_task


def download_subtitle(task_id, url, lang, output_dir):
    temp_template = str(output_dir / f"{task_id}.%(ext)s")

    options = {
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "skip_download": True,
        "writesubtitles": True,
        "subtitleslangs": [lang],
        "subtitlesformat": "best",
        "outtmpl": temp_template,
        "postprocessors": [
            {
                "key": "FFmpegSubtitlesConvertor",
                "format": "srt",
            }
        ],
    }

    apply_cookie_options(options)
    apply_ffmpeg_options(options)
    update_task(task_id, status="processing")

    with yt_dlp.YoutubeDL(options) as ydl:
        info = ydl.extract_info(url, download=True)
        info = pick_first_entry(info)

    candidates = [
        p for p in output_dir.glob(f"{task_id}*")
        if p.is_file() and p.suffix.lower() == ".srt"
    ]

    if not candidates:
        raise RuntimeError("没有生成 SRT 字幕")

    source = max(candidates, key=lambda p: p.stat().st_mtime)

    title = safe_filename(info.get("title") or info.get("id") or "subtitle")
    video_id = info.get("id") or "video"
    safe_lang = safe_filename(lang, 30)

    destination = unique_path(
        output_dir,
        f"{title} [{video_id}] {safe_lang}.srt",
    )

    source.replace(destination)

    for path in output_dir.glob(f"{task_id}*"):
        if path.exists() and path != destination:
            try:
                path.unlink()
            except OSError:
                pass

    update_task(
        task_id,
        status="done",
        progress=100,
        filename=destination.name,
        filepath=str(destination),
        file_size=destination.stat().st_size,
        error=None,
    )



def download_danmaku(task_id, url, output_dir):
    """Download Bilibili danmaku as the original XML track."""
    temp_template = str(output_dir / f"{task_id}.%(ext)s")

    options = {
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "skip_download": True,
        "writesubtitles": True,
        "subtitleslangs": ["danmaku"],
        "subtitlesformat": "xml",
        "outtmpl": temp_template,
    }

    apply_cookie_options(options)
    apply_ffmpeg_options(options)
    update_task(task_id, status="processing")

    with yt_dlp.YoutubeDL(options) as ydl:
        info = ydl.extract_info(url, download=True)
        info = pick_first_entry(info)

    candidates = [
        p for p in output_dir.glob(f"{task_id}*")
        if p.is_file() and p.suffix.lower() == ".xml"
    ]

    if not candidates:
        raise RuntimeError("没有生成弹幕 XML")

    source = max(candidates, key=lambda p: p.stat().st_mtime)

    title = safe_filename(info.get("title") or info.get("id") or "danmaku")
    video_id = info.get("id") or "video"

    destination = unique_path(
        output_dir,
        f"{title} [{video_id}] 弹幕.xml",
    )

    source.replace(destination)

    for path in output_dir.glob(f"{task_id}*"):
        if path.exists() and path != destination:
            try:
                path.unlink()
            except OSError:
                pass

    update_task(
        task_id,
        status="done",
        progress=100,
        filename=destination.name,
        filepath=str(destination),
        file_size=destination.stat().st_size,
        error=None,
    )
