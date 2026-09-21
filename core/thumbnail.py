from urllib.parse import urlparse
from urllib.request import Request, urlopen


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
    Pick the best thumbnail candidate exposed by yt-dlp.

    Bilibili often exposes several thumbnail records. Prefer the candidate
    with the largest known resolution, then remove any CDN resize suffix so
    the downloader can request the original image.
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
    # particular item, fall back to the exact URL yt-dlp supplied.
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
