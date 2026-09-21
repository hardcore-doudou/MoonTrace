import json
import re
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen


BVID_RE = re.compile(r"(BV[0-9A-Za-z]{10})", re.IGNORECASE)
BILIBILI_COVER_WIDTH = 1146
BILIBILI_COVER_HEIGHT = 717


def validate_thumbnail_url(url: str) -> str:
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()

    allowed_hosts = (
        host == "hdslb.com"
        or host.endswith(".hdslb.com")
        or host == "biliimg.com"
        or host.endswith(".biliimg.com")
    )

    if parsed.scheme not in ("http", "https") or not allowed_hosts:
        raise ValueError("不允许的封面地址")

    if parsed.scheme == "http":
        url = "https://" + url[len("http://"):]

    return url


def original_bilibili_thumbnail_url(url: str) -> str:
    safe_url = validate_thumbnail_url(url)
    parsed = urlparse(safe_url)

    path = parsed.path.split("@", 1)[0]
    return parsed._replace(path=path, query="", fragment="").geturl()


def bilibili_standard_cover_url(url: str) -> str:
    """
    Ask Bilibili's own image CDN for the classic 1146x717 cover canvas.

    The source is first normalized to the underlying BFS image. Bilibili then
    performs the resize/crop instead of MoonTrace resizing the downloaded file.
    """
    original = original_bilibili_thumbnail_url(url)
    return (
        f"{original}@{BILIBILI_COVER_WIDTH}w_"
        f"{BILIBILI_COVER_HEIGHT}h_1e_1c.jpg"
    )


def _extract_bvid(info: dict, source_url: str | None = None) -> str | None:
    values = (
        info.get("id"),
        info.get("display_id"),
        info.get("webpage_url"),
        info.get("original_url"),
        source_url,
    )

    for value in values:
        if not isinstance(value, str):
            continue

        match = BVID_RE.search(value)
        if match:
            raw = match.group(1)
            return "BV" + raw[2:]

    return None


def _api_json(url: str, referer: str) -> dict | None:
    request = Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/130.0.0.0 Safari/537.36"
            ),
            "Referer": referer,
            "Accept": "application/json, text/plain, */*",
        },
    )

    try:
        with urlopen(request, timeout=15) as upstream:
            return json.loads(
                upstream.read().decode("utf-8", errors="replace")
            )
    except Exception:
        return None


def get_bilibili_cover_source(
    info: dict,
    source_url: str | None = None,
) -> str | None:
    """
    Prefer Bilibili's richer card metadata.

    Newer Bilibili metadata may expose a higher-resolution 4:3 cover in
    cover43 while the ordinary page thumbnail can be a small 16:9 card image.
    We therefore prefer cover43, then pic, before falling back to yt-dlp.
    """
    bvid = _extract_bvid(info, source_url)

    if bvid:
        referer = f"https://www.bilibili.com/video/{bvid}/"

        cards_url = (
            "https://api.bilibili.com/x/article/cards?"
            + urlencode({"ids": bvid})
        )
        cards = _api_json(cards_url, referer)

        if cards and cards.get("code") == 0:
            data = cards.get("data") or {}

            if isinstance(data, dict):
                entries = [
                    value for value in data.values()
                    if isinstance(value, dict)
                ]

                for entry in entries:
                    entry_bvid = str(entry.get("bvid") or "")
                    if entry_bvid.lower() != bvid.lower():
                        continue

                    for key in ("cover43", "pic"):
                        candidate = entry.get(key)
                        if isinstance(candidate, str) and candidate:
                            try:
                                return original_bilibili_thumbnail_url(candidate)
                            except ValueError:
                                pass

        view_url = (
            "https://api.bilibili.com/x/web-interface/view?"
            + urlencode({"bvid": bvid})
        )
        view = _api_json(view_url, referer)

        if view and view.get("code") == 0:
            data = view.get("data") or {}

            for key in ("cover43", "pic"):
                candidate = data.get(key)
                if isinstance(candidate, str) and candidate:
                    try:
                        return original_bilibili_thumbnail_url(candidate)
                    except ValueError:
                        pass

    return select_best_thumbnail(info)


def get_bilibili_standard_cover(
    info: dict,
    source_url: str | None = None,
) -> str | None:
    source = get_bilibili_cover_source(info, source_url)

    if not source:
        return None

    return bilibili_standard_cover_url(source)


def _thumbnail_score(item: dict) -> tuple[int, int, float, int]:
    width = item.get("width")
    height = item.get("height")
    preference = item.get("preference")
    filesize = item.get("filesize") or item.get("filesize_approx")

    width = int(width) if isinstance(width, (int, float)) else 0
    height = int(height) if isinstance(height, (int, float)) else 0
    preference = (
        float(preference)
        if isinstance(preference, (int, float))
        else 0.0
    )
    filesize = int(filesize) if isinstance(filesize, (int, float)) else 0

    return (
        width * height,
        max(width, height),
        preference,
        filesize,
    )


def select_best_thumbnail(info: dict) -> str | None:
    candidates: list[tuple[tuple[int, int, float, int], str]] = []
    seen: set[str] = set()

    for item in info.get("thumbnails") or []:
        if not isinstance(item, dict):
            continue

        raw_url = item.get("url")

        if not isinstance(raw_url, str) or not raw_url:
            continue

        try:
            url = original_bilibili_thumbnail_url(raw_url)
        except ValueError:
            continue

        if url in seen:
            continue

        seen.add(url)
        candidates.append((_thumbnail_score(item), url))

    fallback = info.get("thumbnail")

    if isinstance(fallback, str) and fallback:
        try:
            fallback_url = original_bilibili_thumbnail_url(fallback)
        except ValueError:
            fallback_url = None

        if fallback_url and fallback_url not in seen:
            candidates.append(((0, 0, 0.0, 0), fallback_url))

    if not candidates:
        return None

    candidates.sort(key=lambda item: item[0], reverse=True)
    return candidates[0][1]


def _suffix_from_response(content_type: str, url: str) -> str:
    content_type = content_type.lower()

    if "png" in content_type:
        return ".png"
    if "webp" in content_type:
        return ".webp"
    if "jpeg" in content_type or "jpg" in content_type:
        return ".jpg"

    path = urlparse(url).path.lower()

    for suffix in (".png", ".webp", ".jpeg", ".jpg"):
        if path.endswith(suffix):
            return ".jpg" if suffix == ".jpeg" else suffix

    return ".jpg"


def fetch_thumbnail(url: str) -> tuple[bytes, str, str]:
    supplied_url = validate_thumbnail_url(url)

    request = Request(
        supplied_url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/130.0.0.0 Safari/537.36"
            ),
            "Referer": "https://www.bilibili.com/",
            "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
        },
    )

    with urlopen(request, timeout=20) as upstream:
        content = upstream.read()
        content_type = upstream.headers.get(
            "Content-Type",
            "image/jpeg",
        ).lower()

    if not content:
        raise RuntimeError("封面响应为空")

    suffix = _suffix_from_response(content_type, supplied_url)
    return content, content_type, suffix
