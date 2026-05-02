from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi.testclient import TestClient
import pytest

from app.main import app
from app.routers.create_session import get_create_session_user
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

    async def list_recent_visits(
        self,
        user: AuthenticatedUser,
        *,
        limit: int,
    ) -> list[dict[str, Any]]:
        return sorted(
            self.visits,
            key=lambda visit: visit["timestamp"],
            reverse=True,
        )[:limit]

    async def get_active_session(
        self,
        user: AuthenticatedUser,
        table: str,
    ) -> dict[str, Any] | None:
        for session in reversed(self.sessions[table]):
            if session["active"]:
                return session
        return None

    async def list_recent_sessions(
        self,
        user: AuthenticatedUser,
        table: str,
        *,
        limit: int,
    ) -> list[dict[str, Any]]:
        return sorted(
            self.sessions[table],
            key=lambda session: session["timestamp"],
            reverse=True,
        )[:limit]

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
    app.dependency_overrides[get_create_session_user] = lambda: USER
    app.dependency_overrides[get_browsing_store] = lambda: store


def test_check_url_requires_supabase_session() -> None:
    response = client.post("/api/check-url", json={"url": "https://example.com/docs"})

    assert response.status_code == 401


def test_check_url_rejects_invalid_url_with_400() -> None:
    _use_store(FakeBrowsingStore())

    response = client.post("/api/check-url", json={"url": "not-a-url"})

    assert response.status_code == 400


def test_create_session_requires_supabase_session() -> None:
    response = client.post(
        "/api/create-session",
        json={"productive": True, "url": "https://example.com/docs"},
    )

    assert response.status_code == 401
    assert response.json() == {
        "error": "UNAUTHORIZED",
        "message": "No active Supabase session found.",
    }


def test_session_visualization_uses_local_backend_without_session() -> None:
    _use_store(FakeBrowsingStore())

    response = client.get("/api/session-visualization")

    assert response.status_code == 200
    assert response.json() == {"sessions": [], "visits": []}


def test_create_session_rejects_invalid_input_with_400() -> None:
    _use_store(FakeBrowsingStore())

    response = client.post(
        "/api/create-session",
        json={"productive": "true", "url": "not-a-url"},
    )

    assert response.status_code == 400
    assert response.json() == {
        "error": "INVALID_REQUEST",
        "message": "productive must be a boolean and url must be valid.",
    }


def test_create_session_continues_existing_productive_session() -> None:
    store = FakeBrowsingStore()
    _use_store(store)
    store.sessions["productive_session"].append(
        {
            "id": "productive-session-1",
            "user_id": USER.id,
            "timestamp": datetime(2026, 5, 2, 20, 0, tzinfo=UTC),
            "active": True,
            "duration": 12.0,
            "visits": [],
        }
    )

    response = client.post(
        "/api/create-session",
        json={
            "productive": True,
            "url": "https://example.com/docs",
            "pageTitle": "Example docs",
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "success": True,
        "action": "productive_session_active",
        "sessionType": "productive",
        "sessionId": "productive-session-1",
        "reason": "Existing productive session continued.",
    }
    assert len(store.sessions["productive_session"]) == 1
    assert store.sessions["productive_session"][0]["visits"] == ["visit-1"]


def test_create_session_starts_procrastination_and_ends_productive_session() -> None:
    store = FakeBrowsingStore()
    _use_store(store)
    store.sessions["productive_session"].append(
        {
            "id": "productive-session-1",
            "user_id": USER.id,
            "timestamp": datetime(2026, 5, 2, 20, 0, tzinfo=UTC),
            "active": True,
            "duration": 12.0,
            "visits": [],
        }
    )

    response = client.post(
        "/api/create-session",
        json={
            "productive": False,
            "url": "https://www.youtube.com/shorts/abc123",
            "pageTitle": "Funny fails compilation",
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "success": True,
        "action": "procrastination_session_active",
        "sessionType": "procrastination",
        "sessionId": "procrastination_session-1",
        "reason": "Productive session ended and procrastination session started.",
    }
    assert store.sessions["productive_session"][0]["active"] is False
    assert len(store.sessions["procrastination_session"]) == 1


def test_create_session_marks_latest_visit_allowed_without_session() -> None:
    store = FakeBrowsingStore()
    app.dependency_overrides[get_browsing_store] = lambda: store
    store.visits.append(
        {
            "id": "visit-1",
            "user_id": USER.id,
            "timestamp": datetime(2026, 5, 2, 20, 0, tzinfo=UTC),
            "duration": 24.0,
            "url": "https://example.com/docs",
            "page_title": "Example docs",
        }
    )
    store.sessions["procrastination_session"].append(
        {
            "id": "procrastination-session-1",
            "user_id": USER.id,
            "timestamp": datetime(2026, 5, 2, 19, 59, tzinfo=UTC),
            "active": True,
            "duration": 12.0,
            "visits": ["visit-1"],
        }
    )

    response = client.post(
        "/api/create-session",
        json={"sessionType": "allowed"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "success": True,
        "action": "allowed_session_active",
        "sessionType": "allowed",
        "sessionId": "allowed_sessions-1",
        "reason": "Current session marked as allowed.",
    }
    assert store.sessions["procrastination_session"][0]["active"] is False
    assert store.sessions["allowed_sessions"][0]["visits"] == ["visit-1"]


def test_session_visualization_returns_recent_activity() -> None:
    store = FakeBrowsingStore()
    _use_store(store)

    older_time = datetime(2026, 5, 2, 19, 0, tzinfo=UTC)
    newer_time = datetime(2026, 5, 2, 20, 0, tzinfo=UTC)
    store.visits.extend(
        [
            {
                "id": "visit-1",
                "user_id": USER.id,
                "timestamp": older_time,
                "duration": 30.0,
                "url": "https://example.com/docs",
                "page_title": "Docs",
            },
            {
                "id": "visit-2",
                "user_id": USER.id,
                "timestamp": newer_time,
                "duration": 90.0,
                "url": "https://example.com/tutorial",
                "page_title": "Tutorial",
            },
        ]
    )
    store.sessions["productive_session"].append(
        {
            "id": "productive-session-1",
            "user_id": USER.id,
            "timestamp": older_time,
            "active": False,
            "duration": 30.0,
            "visits": ["visit-1"],
        }
    )
    store.sessions["allowed_sessions"].append(
        {
            "id": "allowed-session-1",
            "user_id": USER.id,
            "timestamp": newer_time,
            "active": True,
            "duration": 90.0,
            "visits": ["visit-2"],
        }
    )

    response = client.get("/api/session-visualization")

    assert response.status_code == 200
    assert response.json() == {
        "sessions": [
            {
                "id": "allowed-session-1",
                "type": "allowed",
                "timestamp": "2026-05-02T20:00:00Z",
                "active": True,
                "duration": 90.0,
                "visitCount": 1,
                "visits": ["visit-2"],
            },
            {
                "id": "productive-session-1",
                "type": "productive",
                "timestamp": "2026-05-02T19:00:00Z",
                "active": False,
                "duration": 30.0,
                "visitCount": 1,
                "visits": ["visit-1"],
            },
        ],
        "visits": [
            {
                "id": "visit-2",
                "timestamp": "2026-05-02T20:00:00Z",
                "duration": 90.0,
                "url": "https://example.com/tutorial",
                "pageTitle": "Tutorial",
            },
            {
                "id": "visit-1",
                "timestamp": "2026-05-02T19:00:00Z",
                "duration": 30.0,
                "url": "https://example.com/docs",
                "pageTitle": "Docs",
            },
        ],
    }


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


def test_demo_check_url_user1_allows_youtube_from_5_to_6(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "app.routers.check_url._current_demo_datetime",
        lambda: datetime(2026, 5, 2, 17, 15, tzinfo=UTC),
    )

    response = client.post(
        "/api/demo_check_url_user1",
        json={"url": "https://www.youtube.com/watch?v=demo"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "allowed": True,
        "action": "continue",
        "sessionType": "allowed",
        "reason": "Demo user 1: YouTube is allowed from 5 PM to 6 PM.",
        "classification": "okay",
        "confidence": 1.0,
    }


def test_demo_check_url_user1_blocks_youtube_during_8pm_hour(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "app.routers.check_url._current_demo_datetime",
        lambda: datetime(2026, 5, 2, 20, 15, tzinfo=UTC),
    )

    response = client.post(
        "/api/demo_check_url_user1",
        json={"url": "https://www.youtube.com/watch?v=demo"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "allowed": False,
        "action": "hard_ban",
        "sessionType": "procrastination",
        "reason": "Demo user 1: YouTube is blocked during the 8 PM hour.",
        "classification": "bad",
        "confidence": 1.0,
    }


def test_demo_check_url_user2_is_unsure_then_starts_productive_session(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.routers import check_url

    check_url._reset_demo_user2_state()
    current_time = datetime(2026, 5, 2, 17, 0, tzinfo=UTC)
    monkeypatch.setattr(
        "app.routers.check_url._current_demo_datetime",
        lambda: current_time,
    )

    first_response = client.post(
        "/api/demo_check_url_user2",
        json={"url": "https://www.youtube.com/watch?v=demo"},
    )

    current_time = current_time + timedelta(seconds=31)
    second_response = client.post(
        "/api/demo_check_url_user2",
        json={"url": "https://www.youtube.com/watch?v=demo"},
    )

    assert first_response.status_code == 200
    assert first_response.json()["action"] == "ask_user"
    assert first_response.json()["classification"] == "unsure"
    assert second_response.status_code == 200
    assert second_response.json() == {
        "allowed": True,
        "action": "productive_started",
        "sessionType": "productive",
        "reason": (
            "Demo user 2: 30 seconds elapsed, so a productive session has started."
        ),
        "classification": "good",
        "confidence": 1.0,
    }

    check_url._reset_demo_user2_state()


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
