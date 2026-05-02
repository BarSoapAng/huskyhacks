from datetime import UTC, datetime, timedelta

from app.services.debounce import DebounceService


def test_debounce_starts_then_pends_then_expires() -> None:
    service = DebounceService(window_seconds=30)

    assert service.check("youtube.com/shorts/abc") == "started"
    assert service.check("youtube.com/shorts/abc") == "pending"

    state = service._states["youtube.com/shorts/abc"]
    service._states["youtube.com/shorts/abc"] = state.__class__(
        normalized_url=state.normalized_url,
        started_at=state.started_at,
        expires_at=datetime.now(UTC) - timedelta(seconds=1),
    )

    assert service.check("youtube.com/shorts/abc") == "expired"


def test_debounce_is_keyed_by_normalized_url_only() -> None:
    service = DebounceService(window_seconds=30)

    assert service.check("youtube.com/shorts/abc") == "started"
    assert service.check("youtube.com/shorts/def") == "started"
    assert len(service._states) == 2
