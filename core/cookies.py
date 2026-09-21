from config import load_settings, settings_lock


SUPPORTED_COOKIE_BROWSERS = {
    "none",
    "chrome",
    "edge",
    "firefox",
    "brave",
}


def get_cookie_options() -> dict:
    """
    只告诉 yt-dlp 从哪个浏览器/Profile读取 Cookie。
    Cookie 内容本身不会写入 settings.json。
    """
    with settings_lock:
        settings = load_settings()

    browser = str(settings.get("cookie_browser") or "none").lower()
    profile = str(settings.get("cookie_profile") or "").strip() or None

    if browser == "none":
        return {}

    if browser not in SUPPORTED_COOKIE_BROWSERS:
        raise RuntimeError(f"不支持的 Cookie 浏览器：{browser}")

    return {
        "cookiesfrombrowser": (browser, profile, None, None)
    }


def apply_cookie_options(options: dict) -> dict:
    options.update(get_cookie_options())
    return options
