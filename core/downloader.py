import yt_dlp

from core.cookies import apply_cookie_options
from core.ffmpeg import apply_ffmpeg_options
from core.parser import (
    extract_media_info,
    get_available_qualities,
    pick_first_entry,
    safe_filename,
    unique_path,
)
from core.subtitles import download_danmaku, download_subtitle
from core.tasks import update_task
from core.thumbnail import fetch_thumbnail, select_best_thumbnail


def classify_stream(data: dict) -> str:
    info = data.get("info_dict") or {}
    vcodec = info.get("vcodec")
    acodec = info.get("acodec")

    if vcodec and vcodec != "none" and (not acodec or acodec == "none"):
        return "video"

    if acodec and acodec != "none" and (not vcodec or vcodec == "none"):
        return "audio"

    return "file"


def make_progress_hook(task_id: str):
    def hook(data: dict) -> None:
        status = data.get("status")
        stream = classify_stream(data)

        from core.tasks import tasks, tasks_lock

        with tasks_lock:
            task = tasks.get(task_id)
            if not task:
                return

            components = task.setdefault("components", {})
            component = components.setdefault(stream, {})

            if status == "downloading":
                downloaded = data.get("downloaded_bytes") or 0
                total = (
                    data.get("total_bytes")
                    or data.get("total_bytes_estimate")
                    or 0
                )

                progress = None
                if total:
                    progress = round(downloaded / total * 100, 1)

                component.update({
                    "status": "downloading",
                    "progress": progress,
                    "downloaded_bytes": downloaded,
                    "total_bytes": total or None,
                    "speed": data.get("speed"),
                    "eta": data.get("eta"),
                })

                task["status"] = "downloading"

            elif status == "finished":
                component.update({
                    "status": "done",
                    "progress": 100,
                    "speed": None,
                    "eta": None,
                })

                task["status"] = "processing"

    return hook


def download_video(task_id, url, height, output_dir, fragments):
    temp_template = str(output_dir / f"{task_id}.%(ext)s")

    options = {
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "format": (
            f"bestvideo[height<={height}]+bestaudio/"
            f"best[height<={height}]"
        ),
        "outtmpl": temp_template,
        "merge_output_format": "mp4",
        "windowsfilenames": True,
        "concurrent_fragment_downloads": fragments,
        "progress_hooks": [make_progress_hook(task_id)],
    }

    apply_cookie_options(options)
    apply_ffmpeg_options(options)

    with yt_dlp.YoutubeDL(options) as ydl:
        info = ydl.extract_info(url, download=True)
        info = pick_first_entry(info)

    source = output_dir / f"{task_id}.mp4"

    if not source.exists():
        candidates = [
            p for p in output_dir.glob(f"{task_id}.*")
            if p.is_file() and not p.name.endswith((".part", ".ytdl"))
        ]

        if not candidates:
            raise RuntimeError("下载完成，但没有找到输出文件")

        source = max(candidates, key=lambda p: p.stat().st_mtime)

    title = safe_filename(info.get("title") or info.get("id") or "video")
    video_id = info.get("id") or "video"

    selected_quality = next(
        (
            quality
            for quality in get_available_qualities(info)
            if quality.get("height") == height
        ),
        None,
    )
    quality_label = (
        selected_quality.get("label")
        if selected_quality
        else f"{height}P"
    )

    destination = unique_path(
        output_dir,
        f"{title} [{video_id}] {quality_label}.mp4",
    )

    source.replace(destination)

    update_task(
        task_id,
        status="done",
        progress=100,
        filename=destination.name,
        filepath=str(destination),
        file_size=destination.stat().st_size,
        error=None,
    )


def download_audio(task_id, url, output_dir, fragments):
    temp_template = str(output_dir / f"{task_id}.%(ext)s")

    options = {
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "format": "bestaudio[ext=m4a]/bestaudio",
        "outtmpl": temp_template,
        "windowsfilenames": True,
        "concurrent_fragment_downloads": fragments,
        "progress_hooks": [make_progress_hook(task_id)],
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "m4a",
            }
        ],
    }

    apply_cookie_options(options)
    apply_ffmpeg_options(options)

    with yt_dlp.YoutubeDL(options) as ydl:
        info = ydl.extract_info(url, download=True)
        info = pick_first_entry(info)

    source = output_dir / f"{task_id}.m4a"

    if not source.exists():
        candidates = [
            p for p in output_dir.glob(f"{task_id}.*")
            if p.is_file() and not p.name.endswith((".part", ".ytdl"))
        ]

        if not candidates:
            raise RuntimeError("音频处理完成，但没有找到输出文件")

        source = max(candidates, key=lambda p: p.stat().st_mtime)

    title = safe_filename(info.get("title") or info.get("id") or "audio")
    video_id = info.get("id") or "video"

    destination = unique_path(
        output_dir,
        f"{title} [{video_id}].m4a",
    )

    source.replace(destination)

    update_task(
        task_id,
        status="done",
        progress=100,
        filename=destination.name,
        filepath=str(destination),
        file_size=destination.stat().st_size,
        error=None,
    )


def download_cover(task_id, url, output_dir):
    update_task(task_id, status="processing")

    info = extract_media_info(url)
    thumbnail = select_best_thumbnail(info)

    if not thumbnail:
        raise RuntimeError("这个视频没有可用封面")

    content, _, suffix = fetch_thumbnail(thumbnail)

    title = safe_filename(info.get("title") or info.get("id") or "cover")
    video_id = info.get("id") or "video"

    destination = unique_path(
        output_dir,
        f"{title} [{video_id}] 封面{suffix}",
    )

    destination.write_bytes(content)

    update_task(
        task_id,
        status="done",
        progress=100,
        filename=destination.name,
        filepath=str(destination),
        file_size=destination.stat().st_size,
        error=None,
    )


def download_worker(
    task_id,
    url,
    kind,
    height,
    subtitle_lang,
    output_dir,
    fragments,
):
    try:
        update_task(task_id, status="starting")

        if kind == "video":
            if height is None:
                raise RuntimeError("没有指定视频画质")

            download_video(
                task_id,
                url,
                height,
                output_dir,
                fragments,
            )

        elif kind == "audio":
            download_audio(
                task_id,
                url,
                output_dir,
                fragments,
            )

        elif kind == "cover":
            download_cover(
                task_id,
                url,
                output_dir,
            )

        elif kind == "subtitle":
            if not subtitle_lang:
                raise RuntimeError("没有指定字幕语言")

            download_subtitle(
                task_id,
                url,
                subtitle_lang,
                output_dir,
            )

        elif kind == "danmaku":
            download_danmaku(
                task_id,
                url,
                output_dir,
            )

        else:
            raise RuntimeError("未知下载类型")

    except Exception as exc:
        for path in output_dir.glob(f"{task_id}*"):
            try:
                path.unlink()
            except OSError:
                pass

        update_task(
            task_id,
            status="error",
            error=str(exc),
        )
