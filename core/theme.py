"""Local theme settings shared by the browser and desktop window."""

from __future__ import annotations

import json
import os
import re
import tempfile
from pathlib import Path
from threading import Lock

from config import DATA_DIR


THEME_DIR = DATA_DIR / "user_data" / "theme"
THEME_FILE = THEME_DIR / "theme.json"
THEME_CSS_FILE = THEME_DIR / "theme.css"
BACKGROUND_EXTENSIONS = ("png", "jpg", "jpeg", "webp")
BACKGROUND_FILES = tuple(THEME_DIR / f"background.{ext}" for ext in BACKGROUND_EXTENSIONS)
MAX_BACKGROUND_BYTES = 12 * 1024 * 1024
_lock = Lock()
_hex_color = re.compile(r"^#[0-9a-fA-F]{6}$")

PRESETS = {
    "moon": ("#64a8ff", "#776bff", "#c576ff", "#f7f9ff"),
    "aoko": ("#50d5ef", "#468fff", "#c0a8ff", "#f7fbff"),
    "ember": ("#ffc07c", "#ff808d", "#ce84e3", "#fff7f0"),
}


def background_path() -> Path | None:
    return next((p for p in BACKGROUND_FILES if p.is_file()), None)


def _defaults() -> dict:
    a, b, c, text = PRESETS["moon"]
    return {
        "preset": "moon", "accent_a": a, "accent_b": b,
        "accent_c": c, "text": text, "overlay": 36,
        "panel_opacity": 80,
    }


def _validated(data: dict) -> dict:
    preset = data.get("preset", "moon")
    if preset not in (*PRESETS, "custom"):
        raise ValueError("未知的主题预设")
    result = _defaults()
    result["preset"] = preset
    for key in ("accent_a", "accent_b", "accent_c", "text"):
        color = data.get(key, result[key])
        if not isinstance(color, str) or not _hex_color.fullmatch(color):
            raise ValueError(f"主题颜色 {key} 必须是 #RRGGBB")
        result[key] = color.lower()
    for key, minimum, maximum in (("overlay", 0, 80), ("panel_opacity", 40, 96)):
        number = data.get(key, result[key])
        if type(number) is not int or not minimum <= number <= maximum:
            raise ValueError(f"主题参数 {key} 超出范围")
        result[key] = number
    return result


def load_theme() -> dict:
    try:
        saved = json.loads(THEME_FILE.read_text(encoding="utf-8"))
        result = _validated(saved)
    except (OSError, ValueError, TypeError, AttributeError):
        result = _defaults()
    result["background"] = background_path() is not None
    return result


def save_theme(data: dict) -> dict:
    result = _validated(data)
    with _lock:
        THEME_DIR.mkdir(parents=True, exist_ok=True)
        fd, name = tempfile.mkstemp(prefix=".theme-", suffix=".json", dir=THEME_DIR)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as stream:
                json.dump(result, stream, ensure_ascii=False, indent=2)
            os.replace(name, THEME_FILE)
        finally:
            Path(name).unlink(missing_ok=True)
    return load_theme()


def save_background(content: bytes) -> dict:
    if not content or len(content) > MAX_BACKGROUND_BYTES:
        raise ValueError("图片必须小于 12 MB")
    if content.startswith(b"\x89PNG\r\n\x1a\n"):
        ext = "png"
    elif content.startswith(b"\xff\xd8\xff"):
        ext = "jpg"
    elif content.startswith(b"RIFF") and content[8:12] == b"WEBP":
        ext = "webp"
    else:
        raise ValueError("只支持 PNG、JPEG、WebP 图片")
    with _lock:
        THEME_DIR.mkdir(parents=True, exist_ok=True)
        fd, name = tempfile.mkstemp(prefix=".background-", suffix=f".{ext}", dir=THEME_DIR)
        try:
            with os.fdopen(fd, "wb") as stream:
                stream.write(content)
            os.replace(name, THEME_DIR / f"background.{ext}")
            for path in BACKGROUND_FILES:
                if path.suffix != f".{ext}":
                    path.unlink(missing_ok=True)
        finally:
            Path(name).unlink(missing_ok=True)
    return load_theme()


def remove_background() -> dict:
    with _lock:
        for path in BACKGROUND_FILES:
            path.unlink(missing_ok=True)
    return load_theme()
