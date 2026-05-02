from urllib.parse import parse_qsl, urlparse

from app.schemas.check_url import ContentType, NormalizedUrl, Platform


TRACKING_QUERY_PARAMS = {
    "fbclid",
    "gclid",
    "igsh",
    "ref",
    "si",
    "utm_campaign",
    "utm_content",
    "utm_medium",
    "utm_source",
    "utm_term",
}


def normalize_url(url: str) -> NormalizedUrl:
    parsed = urlparse(url.strip())
    hostname = _normalize_hostname(parsed.hostname or "")
    pathname = _normalize_pathname(parsed.path)
    query_params = {
        key: value
        for key, value in parse_qsl(parsed.query, keep_blank_values=True)
        if key
    }

    return NormalizedUrl(
        rawUrl=url.strip(),
        hostname=hostname,
        pathname=pathname,
        queryParams=query_params,
        platform=_detect_platform(hostname),
        contentType=_detect_content_type(hostname, pathname, query_params),
    )


def build_debounce_url_key(normalized: NormalizedUrl) -> str:
    significant_params = {
        key: value
        for key, value in normalized.query_params.items()
        if key.lower() not in TRACKING_QUERY_PARAMS
    }
    query = "&".join(
        f"{key}={value}" for key, value in sorted(significant_params.items())
    )
    base = f"{normalized.hostname}{normalized.pathname}"
    return f"{base}?{query}" if query else base


def _normalize_hostname(hostname: str) -> str:
    hostname = hostname.lower().strip(".")
    if hostname.startswith("www."):
        hostname = hostname[4:]
    if hostname == "m.youtube.com":
        return "youtube.com"
    if hostname == "m.reddit.com":
        return "reddit.com"
    if hostname == "x.com":
        return "twitter.com"
    return hostname


def _normalize_pathname(pathname: str) -> str:
    cleaned = pathname.strip() or "/"
    if not cleaned.startswith("/"):
        cleaned = f"/{cleaned}"
    return cleaned.rstrip("/") or "/"


def _detect_platform(hostname: str) -> Platform:
    if hostname.endswith("youtube.com") or hostname.endswith("youtu.be"):
        return "youtube"
    if hostname.endswith("instagram.com"):
        return "instagram"
    if hostname.endswith("tiktok.com"):
        return "tiktok"
    if hostname.endswith("reddit.com"):
        return "reddit"
    if hostname.endswith("twitter.com"):
        return "twitter"
    return "unknown"


def _detect_content_type(
    hostname: str,
    pathname: str,
    query_params: dict[str, str],
) -> ContentType:
    path = pathname.lower()

    if hostname.endswith("youtube.com"):
        if path.startswith("/shorts/"):
            return "shorts"
        if path == "/watch" and "v" in query_params:
            return "video"
        if path == "/results":
            return "search"
        if path in {"/", "/feed", "/feed/subscriptions"}:
            return "feed"
        if (
            path.startswith("/@")
            or path.startswith("/channel/")
            or path.startswith("/c/")
        ):
            return "profile"

    if hostname.endswith("instagram.com"):
        if path.startswith("/reels") or path.startswith("/reel/"):
            return "shorts"
        if path.startswith("/explore"):
            return "feed"
        if path.count("/") <= 1 and path != "/":
            return "profile"

    if hostname.endswith("tiktok.com"):
        if "/video/" in path:
            return "video"
        if path.startswith("/@"):
            return "profile"
        return "feed"

    if hostname.endswith("reddit.com"):
        if path in {"/r/all", "/r/popular"}:
            return "feed"
        if "/comments/" in path:
            return "video" if path.endswith("/video") else "unknown"
        if path.startswith("/r/") or path in {"/", "/best", "/hot"}:
            return "feed"

    if hostname.endswith("twitter.com"):
        if path == "/search":
            return "search"
        if path.count("/") <= 1 and path != "/":
            return "profile"
        return "feed"

    return "unknown"
