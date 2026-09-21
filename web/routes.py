from pathlib import Path
from urllib.parse import quote
import subprocess
import tkinter as tk
from tkinter import filedialog

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel

from config import (
    BASE_DIR,
    STATIC_DIR,
    load_settings,
    save_settings,
    settings_lock,
    resolve_output_dir,
)
from core.cookies import SUPPORTED_COOKIE_BROWSERS
from core.downloader import download_worker
from core.ffmpeg import ffmpeg_available
from core.parser import (
    normalize_media_url,
    extract_media_info,
    get_available_qualities,
    get_subtitle_languages,
    has_danmaku,
)
from core.platforms import detect_platform
from core.tasks import create_task, get_task
from core.thumbnail import fetch_thumbnail, get_official_bilibili_thumbnail


router = APIRouter()


class ParseRequest(BaseModel):
    url: str


class DownloadRequest(BaseModel):
    url: str
    kind: str
    height: int | None = None
    subtitle_lang: str | None = None
    output_dir: str | None = None
    concurrent_fragments: int = 4


class SettingsRequest(BaseModel):
    download_dir: str | None = None
    ask_each_time: bool | None = None
    concurrent_fragments: int | None = None
    cookie_browser: str | None = None
    cookie_profile: str | None = None


def select_folder_windows(initial: str) -> str | None:
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)

    try:
        selected = filedialog.askdirectory(
            title="选择 BiliDownloader 保存位置",
            initialdir=initial if Path(initial).exists() else str(BASE_DIR),
            mustexist=False,
        )
    finally:
        root.destroy()

    return selected or None


@router.get("/")
def home():
    return FileResponse(STATIC_DIR / "index.html")


@router.get("/api/settings")
def get_settings():
    with settings_lock:
        return load_settings()


@router.post("/api/settings")
def update_settings(data: SettingsRequest):
    with settings_lock:
        settings = load_settings()

        if data.download_dir is not None:
            path = Path(data.download_dir).expanduser()

            if not path.is_absolute():
                raise HTTPException(
                    status_code=400,
                    detail="保存目录必须是绝对路径",
                )

            path.mkdir(parents=True, exist_ok=True)
            settings["download_dir"] = str(path.resolve())

        if data.ask_each_time is not None:
            settings["ask_each_time"] = data.ask_each_time

        if data.concurrent_fragments is not None:
            if data.concurrent_fragments not in (1, 4, 8):
                raise HTTPException(
                    status_code=400,
                    detail="并发分片只支持 1、4、8",
                )

            settings["concurrent_fragments"] = data.concurrent_fragments

        if data.cookie_browser is not None:
            browser = data.cookie_browser.lower().strip()

            if browser not in SUPPORTED_COOKIE_BROWSERS:
                raise HTTPException(
                    status_code=400,
                    detail="不支持的 Cookie 浏览器",
                )

            settings["cookie_browser"] = browser

        if data.cookie_profile is not None:
            settings["cookie_profile"] = data.cookie_profile.strip()

        save_settings(settings)
        return settings


@router.post("/api/select-folder")
def select_folder():
    with settings_lock:
        settings = load_settings()

    try:
        selected = select_folder_windows(
            settings["download_dir"]
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"无法打开 Windows 文件夹选择器：{exc}",
        ) from exc

    if not selected:
        return {"cancelled": True}

    path = Path(selected).resolve()
    path.mkdir(parents=True, exist_ok=True)

    return {
        "cancelled": False,
        "path": str(path),
    }


@router.get("/api/thumbnail")
def proxy_thumbnail(url: str = Query(...)):
    try:
        content, content_type, _ = fetch_thumbnail(url)
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"封面获取失败：{exc}",
        ) from exc

    return Response(
        content=content,
        media_type=content_type,
        headers={
            "Cache-Control": "public, max-age=3600"
        },
    )


@router.post("/api/parse")
def parse_video(data: ParseRequest):
    try:
        url = normalize_media_url(data.url)
        info = extract_media_info(url)
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=f"解析失败：{exc}",
        ) from exc

    thumbnail = get_official_bilibili_thumbnail(info, url)
    platform = detect_platform(url)

    return {
        "platform": platform.key,
        "platform_name": platform.display_name,
        "title": info.get("title") or "未知标题",
        "uploader": (
            info.get("uploader")
            or info.get("channel")
            or "未知 UP 主"
        ),
        "duration": info.get("duration"),
        "thumbnail": thumbnail,
        "thumbnail_proxy": (
            f"/api/thumbnail?url={quote(thumbnail, safe='')}"
            if thumbnail else None
        ),
        "webpage_url": info.get("webpage_url") or url,
        "id": info.get("id"),
        "qualities": get_available_qualities(info),
        "subtitles": get_subtitle_languages(info),
        "danmaku": has_danmaku(info),
    }


@router.post("/api/download")
def start_download(
    data: DownloadRequest,
    background_tasks: BackgroundTasks,
):
    if (
        data.kind in ("video", "audio", "subtitle")
        and not ffmpeg_available()
    ):
        raise HTTPException(
            status_code=500,
            detail=(
                "找不到 FFmpeg。请重新运行 setup.bat，"
                "它会自动安装 MoonTrace 所需的 FFmpeg。"
            ),
        )

    if data.kind not in ("video", "audio", "cover", "subtitle", "danmaku"):
        raise HTTPException(
            status_code=400,
            detail="不支持的下载类型",
        )

    if data.kind == "video":
        if (
            data.height is None
            or data.height < 144
            or data.height > 4320
        ):
            raise HTTPException(
                status_code=400,
                detail="无效的视频画质",
            )

    if data.concurrent_fragments not in (1, 4, 8):
        raise HTTPException(
            status_code=400,
            detail="并发分片只支持 1、4、8",
        )

    try:
        url = normalize_media_url(data.url)
        output_dir = resolve_output_dir(data.output_dir)
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    task_id = create_task(
        kind=data.kind,
        height=data.height,
        subtitle_lang=data.subtitle_lang,
        output_dir=str(output_dir),
    )

    background_tasks.add_task(
        download_worker,
        task_id,
        url,
        data.kind,
        data.height,
        data.subtitle_lang,
        output_dir,
        data.concurrent_fragments,
    )

    return {"task_id": task_id}


@router.get("/api/tasks/{task_id}")
def task_status(task_id: str):
    task = get_task(task_id)

    if not task:
        raise HTTPException(
            status_code=404,
            detail="任务不存在",
        )

    return task


@router.get("/api/files/{task_id}")
def get_downloaded_file(task_id: str):
    task = get_task(task_id)

    if not task:
        raise HTTPException(
            status_code=404,
            detail="任务不存在",
        )

    if (
        task.get("status") != "done"
        or not task.get("filepath")
    ):
        raise HTTPException(
            status_code=409,
            detail="文件还没有准备好",
        )

    path = Path(task["filepath"]).resolve()

    if not path.exists():
        raise HTTPException(
            status_code=404,
            detail="文件不存在",
        )

    return FileResponse(
        path=path,
        filename=task["filename"],
    )


@router.post("/api/open-folder/{task_id}")
def open_folder(task_id: str):
    task = get_task(task_id)

    if not task or not task.get("filepath"):
        raise HTTPException(
            status_code=404,
            detail="任务文件不存在",
        )

    path = Path(task["filepath"]).resolve()

    if not path.exists():
        raise HTTPException(
            status_code=404,
            detail="文件不存在",
        )

    subprocess.Popen(
        ["explorer.exe", "/select,", str(path)]
    )

    return {"ok": True}
