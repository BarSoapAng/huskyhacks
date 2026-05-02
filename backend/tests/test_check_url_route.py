from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
import pytest

from app.main import app
from app.core.settings import get_settings
from app.services.debounce import debounce_service


client = TestClient(app)


def setup_function() -> None:
    debounce_service._states.clear()


def test_check_url_allows_safe_url_without_gemini() -> None:
    response = client.post("/api/check-url", json={"url": "https://example.com/docs"})

    assert response.status_code == 200
    assert response.json() == {
        "allowed": True,
        "action": "allow",
        "procrastinationScore": None,
        "reason": None,
        "confidence": None,
        "source": "safe_url",
    }


def test_check_url_starts_debounce_for_bad_url() -> None:
    response = client.post(
        "/api/check-url",
        json={
            "url": "https://www.youtube.com/shorts/abc123?si=test",
            "pageTitle": "Funny fails compilation",
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "allowed": True,
        "action": "allow",
        "procrastinationScore": None,
        "reason": "Debounce started for potentially distracting URL.",
        "confidence": None,
        "source": "debounce_pending",
    }


def test_check_url_reports_pending_debounce_for_same_bad_url() -> None:
    body = {
        "url": "https://www.youtube.com/shorts/abc123?si=test",
        "pageTitle": "Funny fails compilation",
    }

    client.post("/api/check-url", json=body)
    response = client.post("/api/check-url", json=body)

    assert response.status_code == 200
    assert response.json()["source"] == "debounce_pending"
    assert response.json()["reason"] == "Debounce still pending."


def test_check_url_requires_gemini_after_debounce_expires_without_key() -> None:
    if get_settings().gemini_api_key:
        pytest.skip("GEMINI_API_KEY is configured; live Gemini route covered elsewhere.")

    body = {
        "url": "https://www.youtube.com/shorts/abc123?si=test",
        "pageTitle": "Funny fails compilation",
    }

    client.post("/api/check-url", json=body)
    key = next(iter(debounce_service._states))
    state = debounce_service._states[key]
    debounce_service._states[key] = state.__class__(
        normalized_url=state.normalized_url,
        started_at=state.started_at,
        expires_at=datetime.now(UTC) - timedelta(seconds=1),
    )

    response = client.post("/api/check-url", json=body)

    assert response.status_code == 503
    assert response.json() == {"detail": "GEMINI_API_KEY is not configured."}
