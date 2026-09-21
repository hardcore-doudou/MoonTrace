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


def fetch_thumbnail(url: str) -> tuple[bytes, str, str]:
    safe_url = validate_thumbnail_url(url)

    request = Request(
        safe_url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 Chrome/130 Safari/537.36"
            ),
            "Referer": "https://www.bilibili.com/",
        },
    )

    with urlopen(request, timeout=20) as upstream:
        content = upstream.read()
        content_type = upstream.headers.get("Content-Type", "image/jpeg").lower()

    suffix = ".jpg"

    if "png" in content_type:
        suffix = ".png"
    elif "webp" in content_type:
        suffix = ".webp"

    return content, content_type, suffix
