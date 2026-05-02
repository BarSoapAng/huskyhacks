from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi.testclient import TestClient
import pytest

from app.main import app
from app.routers.check_url import get_browsing_store, get_current_user
from app.schemas.ai import LearningCheckOutput, LinkClassificationOutput
from app.schemas.check_url import CheckUrlRequest
from app.services.gemini_client import GeminiGenerationError
from app.services.supabase_client import AuthenticatedUser
from app.services.url_classifier import classify_url


client = TestClient(app)
USER = AuthenticatedUser(
    id="00000000-0000-0000-0000-000000000001",
    access_token="test-token",
)


class FakeBrowsingStore:
    def __init__(self, bad_domains: list[str] | None = None) -> None:
        self.bad_domains = bad_domains or []
        self.visits: list[dict[str, Any]] = []
        self.sessions: dict[str, list[dict[str, Any]]] = {
            "procrastination_session": [],
            "productive_session": [],
            "allowed_sessions": [],
        }

    async def list_bad_domains(self, user: AuthenticatedUser) -> list[str]:
        return self.bad_domains

    async def get_latest_visit(
        self,
        user: AuthenticatedUser,
    ) -> dict[str, Any] | None:
        return self.visits[-1] if self.visits else None

    async def create_visit(
        self,
        user: AuthenticatedUser,
        *,
        url: str,
        normalized_url: str,
        domain: str,
        page_title: str,
        now: datetime,
    ) -> dict[str, Any]:
        visit = {
            "id": f"visit-{len(self.visits) + 1}",
            "user_id": user.id,
            "timestamp": now,
            "duration": 0.0,
            "url": url,
            "normalized_url": normalized_url,
            "domain": domain,
            "page_title": page_title,
            "last_seen_at": now,
        }
        self.visits.append(visit)
        return visit

    async def update_visit(
        self,
        user: AuthenticatedUser,
        visit: dict[str, Any],
        *,
        duration: float,
        page_title: str,
        now: datetime,
    ) -> dict[str, Any]:
        visit.update(
            {
                "duration": duration,
                "page_title": page_title,
                "last_seen_at": now,
            }
        )
        return visit

    async def get_active_session(
        self,
        user: AuthenticatedUser,
        table: str,
    ) -> dict[str, Any] | None:
        for session in reversed(self.sessions[table]):
            if session["active"]:
                return session
        return None

    async def create_session(
        self,
        user: AuthenticatedUser,
        table: str,
        *,
        visit_id: str,
        now: datetime,
        duration: float = 0,
    ) -> dict[str, Any]:
        session = {
            "id": f"{table}-{len(self.sessions[table]) + 1}",
            "user_id": user.id,
            "timestamp": now,
            "active": True,
            "duration": duration,
            "visits": [visit_id],
        }
        self.sessions[table].append(session)
        return session

    async def update_session(
        self,
        user: AuthenticatedUser,
        table: str,
        session: dict[str, Any],
        updates: dict[str, Any],
    ) -> dict[str, Any]:
        session.update(updates)
        return session


def setup_function() -> None:
    app.dependency_overrides.clear()


def teardown_function() -> None:
    app.dependency_overrides.clear()


def _use_store(store: FakeBrowsingStore) -> None:
    app.dependency_overrides[get_current_user] = lambda: USER
    app.dependency_overrides[get_browsing_store] = lambda: store


def test_check_url_requires_supabase_session() -> None:
    response = client.post("/api/check-url", json={"url": "https://example.com/docs"})

    assert response.status_code == 401


def test_check_url_rejects_invalid_url_with_400() -> None:
    _use_store(FakeBrowsingStore())

    response = client.post("/api/check-url", json={"url": "not-a-url"})

    assert response.status_code == 400


def test_check_url_allows_good_url_and_starts_sessions() -> None:
    store = FakeBrowsingStore()
    _use_store(store)

    response = client.post("/api/check-url", json={"url": "https://example.com/docs"})

    assert response.status_code == 200
    assert response.json() == {
        "allowed": True,
        "action": "productive_started",
        "sessionType": "productive",
        "reason": None,
        "classification": "good",
        "confidence": None,
    }
    assert store.visits[0]["page_title"] == ""
    assert len(store.sessions["allowed_sessions"]) == 1
    assert len(store.sessions["productive_session"]) == 1


def test_check_url_hard_bans_only_after_bad_gemini_classification(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = FakeBrowsingStore(bad_domains=["youtube.com/shorts"])
    _use_store(store)

    async def learning_check(
        request: CheckUrlRequest,
        normalized: object,
    ) -> LearningCheckOutput:
        return LearningCheckOutput(
            isLearning=False,
            confidence=0.95,
            reason="Entertainment.",
        )

    async def classification_check(
        request: CheckUrlRequest,
        normalized: object,
    ) -> LinkClassificationOutput:
        return LinkClassificationOutput(
            classification="bad",
            confidence=0.9,
            reason="Short-form entertainment.",
        )

    monkeypatch.setattr(
        "app.services.url_classifier.call_gemini_learning_analyzer",
        learning_check,
    )
    monkeypatch.setattr(
        "app.services.url_classifier.call_gemini_classification_analyzer",
        classification_check,
    )

    response = client.post(
        "/api/check-url",
        json={
            "url": "https://www.youtube.com/shorts/abc123?si=test",
            "pageTitle": "Funny fails compilation",
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "allowed": False,
        "action": "hard_ban",
        "sessionType": "procrastination",
        "reason": "Short-form entertainment.",
        "classification": "bad",
        "confidence": 0.9,
    }
    assert len(store.sessions["procrastination_session"]) == 1


def test_check_url_asks_user_if_gemini_classification_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = FakeBrowsingStore(bad_domains=["youtube.com/shorts"])
    _use_store(store)

    async def learning_check(
        request: CheckUrlRequest,
        normalized: object,
    ) -> LearningCheckOutput:
        return LearningCheckOutput(
            isLearning=False,
            confidence=0.95,
            reason="Not learning.",
        )

    async def classification_check(
        request: CheckUrlRequest,
        normalized: object,
    ) -> LinkClassificationOutput:
        raise GeminiGenerationError("Gemini request failed.")

    monkeypatch.setattr(
        "app.services.url_classifier.call_gemini_learning_analyzer",
        learning_check,
    )
    monkeypatch.setattr(
        "app.services.url_classifier.call_gemini_classification_analyzer",
        classification_check,
    )

    response = client.post(
        "/api/check-url",
        json={
            "url": "https://www.youtube.com/shorts/abc123",
            "pageTitle": "Funny fails compilation",
        },
    )

    assert response.status_code == 200
    assert response.json()["action"] == "ask_user"
    assert response.json()["classification"] == "unsure"


@pytest.mark.anyio
async def test_same_url_poll_extends_current_visit_without_duplicate_rows() -> None:
    store = FakeBrowsingStore()
    first_poll = datetime(2026, 5, 2, 20, 0, tzinfo=UTC)
    request = CheckUrlRequest(
        url="https://example.com/docs",
        pageTitle="Example docs",
    )

    await classify_url(request, user=USER, store=store, now=first_poll)
    response = await classify_url(
        request,
        user=USER,
        store=store,
        now=first_poll + timedelta(seconds=1.5),
    )

    assert response.action == "continue"
    assert len(store.visits) == 1
    assert store.visits[0]["duration"] == 1.5
    assert store.sessions["productive_session"][0]["duration"] == 1.5
