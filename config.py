from pathlib import Path
from threading import Lock
import json


BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
DOWNLOAD_DIR = BASE_DIR / "downloads"
SETTINGS_FILE = BASE_DIR / "settings.json"

DOWNLOAD_DIR.mkdir(exist_ok=True)

settings_lock = Lock()

DEFAULT_SETTINGS = {
    "download_dir": str(DOWNLOAD_DIR),
    "ask_each_time": False,
    "concurrent_fragments": 4,
    "cookie_browser": "none",
    "cookie_profile": "",
}


def save_settings(settings: dict) -> None:
    SETTINGS_FILE.write_text(
        json.dumps(settings, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def load_settings() -> dict:
    if not SETTINGS_FILE.exists():
        save_settings(DEFAULT_SETTINGS)
        return dict(DEFAULT_SETTINGS)

    try:
        data = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
    except Exception:
        data = {}

    merged = dict(DEFAULT_SETTINGS)
    merged.update({k: v for k, v in data.items() if k in merged})
    return merged


def resolve_output_dir(raw: str | None = None) -> Path:
    if raw:
        path = Path(raw).expanduser()
    else:
        with settings_lock:
            path = Path(load_settings()["download_dir"])

    if not path.is_absolute():
        raise ValueError("保存目录必须是绝对路径")

    path.mkdir(parents=True, exist_ok=True)
    return path.resolve()
