from urllib.parse import urlparse
import re

import yt_dlp

from core.cookies import apply_cookie_options
from core.ffmpeg import apply_ffmpeg_options


def normalize_media_url(raw: str) -> str:
    value = raw.strip()

    if value.upper().startswith("BV") and "/" not in value and "." not in value:
        return f"https://www.bilibili.com/video/{value}"

    if "://" not in value:
        value = "https://" + value

    parsed = urlparse(value)
    host = (parsed.hostname or "").lower()

    allowed = (
        host == "bilibili.com"
        or host.endswith(".bilibili.com")
        or host == "b23.tv"
        or host.endswith(".b23.tv")
    )

    if not allowed:
        raise ValueError("MoonTrace 目前只启用了 Bilibili / b23.tv 支持")

    return value


def pick_first_entry(info: dict) -> dict:
    if isinstance(info, dict) and info.get("entries"):
        entries = [item for item in info["entries"] if item]
        if entries:
            return entries[0]
    return info


def safe_filename(value: str, max_length: int = 120) -> str:
    value = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", value)
    value = value.strip(" .")

    if not value:
        value = "video"

    return value[:max_length].rstrip(" .")


def unique_path(directory, filename: str):
    destination = directory / filename

    if not destination.exists():
        return destination

    stem = destination.stem
    suffix = destination.suffix
    counter = 2

    while True:
        candidate = directory / f"{stem} ({counter}){suffix}"
        if not candidate.exists():
            return candidate
        counter += 1


BILIBILI_QUALITY_LABELS = {
    6: "240P",
    16: "360P",
    32: "480P",
    64: "720P",
    74: "720P",
    80: "1080P",
    112: "1080P+",
    116: "1080P",
    120: "4K",
    125: "HDR",
    126: "杜比视界",
    127: "8K",
}

SUBTITLE_DISPLAY_NAMES = {
    "ai-zh": "AI 中文",
    "zh-CN": "简体中文",
    "zh-Hans": "简体中文",
    "zh-Hant": "繁體中文",
    "zh-TW": "繁體中文",
    "en": "English",
    "ja": "日本語",
}


def _format_quality_label(fmt: dict) -> str:
    quality_id = fmt.get("quality")

    if isinstance(quality_id, (int, float)):
        mapped = BILIBILI_QUALITY_LABELS.get(int(quality_id))
        if mapped:
            return mapped

    for key in ("format_note", "format"):
        value = fmt.get(key)

        if not value:
            continue

        match = re.search(
            r"(?i)(8K|4K|\d{3,4}P\+?)",
            str(value),
        )
        if match:
            label = match.group(1).upper()
            return label.replace("P+", "P+")

    width = fmt.get("width")
    height = fmt.get("height")

    if isinstance(width, (int, float)) and isinstance(height, (int, float)):
        # 对未知格式不再把竖屏 height 错叫成“xxxxP”；
        # 直接显示真实像素尺寸更准确。
        return f"{int(width)}×{int(height)}"

    if isinstance(height, (int, float)):
        return f"{int(height)}P"

    return "未知画质"


def get_available_qualities(info: dict) -> list[dict]:
    qualities: dict[object, dict] = {}

    for fmt in info.get("formats") or []:
        height = fmt.get("height")
        width = fmt.get("width")
        fps = fmt.get("fps")
        vcodec = fmt.get("vcodec")
        quality_id = fmt.get("quality")
        tbr = fmt.get("tbr")

        if not isinstance(height, (int, float)) or not height:
            continue

        if not vcodec or vcodec == "none":
            continue

        height = int(height)
        width = int(width) if isinstance(width, (int, float)) else None
        quality_id = (
            int(quality_id)
            if isinstance(quality_id, (int, float))
            else None
        )

        # Bilibili 同一画质会因为 AVC / HEVC / AV1 出现多个格式。
        # 有 quality(qn) 时按官方画质档位去重；否则退回实际分辨率。
        dedupe_key = (
            ("quality", quality_id)
            if quality_id is not None
            else ("resolution", width, height)
        )

        candidate = {
            "height": height,          # 实际像素高度，用于下载选择
            "width": width,
            "fps": float(fps) if isinstance(fps, (int, float)) else None,
            "quality_id": quality_id,
            "label": _format_quality_label(fmt),
            "tbr": float(tbr) if isinstance(tbr, (int, float)) else None,
        }

        previous = qualities.get(dedupe_key)

        def score(item: dict | None) -> tuple[float, float]:
            if not item:
                return (0.0, 0.0)
            return (
                float(item.get("fps") or 0),
                float(item.get("tbr") or 0),
            )

        if previous is None or score(candidate) > score(previous):
            qualities[dedupe_key] = candidate

    result = list(qualities.values())

    def sort_key(item: dict) -> tuple[int, int]:
        return (
            int(item.get("quality_id") or 0),
            int(item.get("height") or 0),
        )

    result.sort(key=sort_key, reverse=True)
    return result


def get_subtitle_languages(info: dict) -> list[dict]:
    result = []
    subtitles = info.get("subtitles") or {}

    for lang, tracks in subtitles.items():
        if not tracks:
            continue

        # yt-dlp 的 Bilibili extractor 会把弹幕 XML 放进 subtitles
        # 的 danmaku 轨；MoonTrace 单独把它作为“弹幕”处理。
        if str(lang).lower() == "danmaku":
            continue

        name = SUBTITLE_DISPLAY_NAMES.get(lang, lang)
        first = tracks[0] if isinstance(tracks, list) and tracks else {}

        if isinstance(first, dict):
            name = (
                first.get("name")
                or SUBTITLE_DISPLAY_NAMES.get(lang)
                or lang
            )

        result.append({
            "id": lang,
            "name": name,
        })

    return result


def has_danmaku(info: dict) -> bool:
    subtitles = info.get("subtitles") or {}
    return bool(subtitles.get("danmaku"))


def extract_media_info(url: str) -> dict:
    options = {
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "skip_download": True,
        "listsubtitles": True,
    }

    apply_cookie_options(options)
    apply_ffmpeg_options(options)

    with yt_dlp.YoutubeDL(options) as ydl:
        info = ydl.extract_info(url, download=False)
        return pick_first_entry(ydl.sanitize_info(info))


# Compatibility aliases during the MoonTrace migration.
# New code should prefer normalize_media_url / extract_media_info.
normalize_bilibili_url = normalize_media_url
extract_info_basic = extract_media_info
