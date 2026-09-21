import json
import re
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen


BVID_RE = re.compile(r"(BV[0-9A-Za-z]{10})", re.IGNORECASE)


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
    """
    Bilibili CDN image URLs may append resize/crop instructions after "@",
    for example: cover.jpg@672w_378h_1c.webp.

    Removing that suffix asks the CDN for the original stored image.
    """
    safe_url = validate_thumbnail_url(url)
    parsed = urlparse(safe_url)

    if "@" not in parsed.path:
        return safe_url

    original_path = parsed.path.split("@", 1)[0]
    return parsed._replace(path=original_path).geturl()


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


def get_official_bilibili_thumbnail(
    info: dict,
    source_url: str | None = None,
) -> str | None:
    """
    Get the actual Bilibili submission cover from the official video-info API.

    The x/web-interface/view endpoint exposes data.pic, which is the video's
    cover image rather than a page-sized preview thumbnail. If the API cannot
    be reached, fall back to the thumbnail metadata provided by yt-dlp.
    """
    bvid = _extract_bvid(info, source_url)

    if bvid:
        api_url = (
            "https://api.bilibili.com/x/web-interface/view?"
            + urlencode({"bvid": bvid})
        )

        request = Request(
            api_url,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 Chrome/130 Safari/537.36"
                ),
                "Referer": f"https://www.bilibili.com/video/{bvid}/",
                "Accept": "application/json, text/plain, */*",
            },
        )

        try:
            with urlopen(request, timeout=15) as upstream:
                payload = json.loads(
                    upstream.read().decode("utf-8", errors="replace")
                )

            if payload.get("code") == 0:
                data = payload.get("data") or {}
                pic = data.get("pic")

                if isinstance(pic, str) and pic:
                    return original_bilibili_thumbnail_url(pic)

        except Exception:
            # Keep cover downloads usable if the API is temporarily blocked,
            # rate-limited or unavailable.
            pass

    return select_best_thumbnail(info)


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
    """
    Fallback thumbnail selection for cases where the Bilibili API cannot be
    used. Prefer the largest candidate exposed by yt-dlp.
    """
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
    original_url = original_bilibili_thumbnail_url(supplied_url)

    # Prefer the original CDN image. If Bilibili refuses that URL for a
    # particular item, fall back to the exact URL supplied to us.
    urls = [original_url]
    if supplied_url != original_url:
        urls.append(supplied_url)

    last_error: Exception | None = None

    for candidate in urls:
        request = Request(
            candidate,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 Chrome/130 Safari/537.36"
                ),
                "Referer": "https://www.bilibili.com/",
            },
        )

        try:
            with urlopen(request, timeout=20) as upstream:
                content = upstream.read()
                content_type = upstream.headers.get(
                    "Content-Type",
                    "image/jpeg",
                ).lower()

            if not content:
                raise RuntimeError("封面响应为空")

            suffix = _suffix_from_response(content_type, candidate)
            return content, content_type, suffix

        except Exception as exc:
            last_error = exc

    raise RuntimeError(f"封面获取失败：{last_error}")
