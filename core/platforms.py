from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse


@dataclass(frozen=True)
class PlatformInfo:
    key: str
    display_name: str
    emoji: str


SUPPORTED_PLATFORMS = {
    "bilibili": PlatformInfo(
        key="bilibili",
        display_name="Bilibili",
        emoji="📺",
    ),
}


def detect_platform(raw: str) -> PlatformInfo:
    """
    Detect which platform a user input belongs to.

    MoonTrace currently enables Bilibili only.
    YouTube / TikTok adapters can be added here later without rewriting
    the Web or Telegram layers.
    """
    value = raw.strip()

    if value.upper().startswith("BV") and "/" not in value and "." not in value:
        return SUPPORTED_PLATFORMS["bilibili"]

    candidate = value
    if "://" not in candidate:
        candidate = "https://" + candidate

    host = (urlparse(candidate).hostname or "").lower()

    if (
        host == "bilibili.com"
        or host.endswith(".bilibili.com")
        or host == "b23.tv"
        or host.endswith(".b23.tv")
    ):
        return SUPPORTED_PLATFORMS["bilibili"]

    raise ValueError("MoonTrace 目前只启用了 Bilibili 支持")
