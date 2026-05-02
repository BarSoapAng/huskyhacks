from app.utils.normalize_url import build_debounce_url_key, normalize_url


def test_normalize_youtube_shorts_url() -> None:
    normalized = normalize_url("https://www.youtube.com/shorts/abc123?si=test")

    assert normalized.raw_url == "https://www.youtube.com/shorts/abc123?si=test"
    assert normalized.hostname == "youtube.com"
    assert normalized.pathname == "/shorts/abc123"
    assert normalized.query_params == {"si": "test"}
    assert normalized.platform == "youtube"
    assert normalized.content_type == "shorts"


def test_build_debounce_key_removes_tracking_params() -> None:
    normalized = normalize_url(
        "https://m.youtube.com/shorts/abc123?si=test&utm_source=x&feature=share"
    )

    assert build_debounce_url_key(normalized) == "youtube.com/shorts/abc123?feature=share"


def test_browser_internal_url_is_unknown_and_safe_shape() -> None:
    normalized = normalize_url("about:blank")

    assert normalized.hostname == ""
    assert normalized.pathname == "/blank"
    assert normalized.query_params == {}
    assert normalized.platform == "unknown"
    assert normalized.content_type == "unknown"
