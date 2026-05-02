from datetime import UTC, datetime
from typing import Any

from fastapi.testclient import TestClient

from app.main import app
from app.routers.create_session import LOCAL_DEMO_USER_ID, get_browsing_store
from app.services.supabase_client import AuthenticatedUser


client = TestClient(app)


class FakeBrowsingStore:
    def __init__(self) -> None:
        self.visits: list[dict[str, Any]] = []
        self.sessions: dict[str, list[dict[str, Any]]] = {
            "procrastination_session": [],
            "productive_session": [],
            "allowed_sessions": [],
        }

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


def test_demo_mark_current_session_unproductive_creates_active_procrastination() -> None:
    store = FakeBrowsingStore()
    app.dependency_overrides[get_browsing_store] = lambda: store
    store.sessions["productive_session"].append(
        {
            "id": "productive-session-1",
            "user_id": LOCAL_DEMO_USER_ID,
            "timestamp": datetime(2026, 5, 2, 20, 0, tzinfo=UTC),
            "active": True,
            "duration": 12.0,
            "visits": [],
        }
    )
    store.sessions["procrastination_session"].append(
        {
            "id": "procrastination-session-1",
            "user_id": LOCAL_DEMO_USER_ID,
            "timestamp": datetime(2026, 5, 2, 19, 0, tzinfo=UTC),
            "active": True,
            "duration": 30.0,
            "visits": [],
        }
    )

    response = client.post(
        "/api/demo/mark-current-session-unproductive",
        json={
            "url": "https://www.youtube.com/watch?v=demo",
            "pageTitle": "Demo video",
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "success": True,
        "action": "procrastination_session_active",
        "sessionType": "procrastination",
        "sessionId": "procrastination_session-2",
        "reason": "Current session marked as unproductive.",
    }
    assert store.sessions["productive_session"][0]["active"] is False
    assert store.sessions["procrastination_session"][0]["active"] is False
    assert store.sessions["procrastination_session"][1]["active"] is True
    assert store.sessions["procrastination_session"][1]["user_id"] == LOCAL_DEMO_USER_ID
    assert store.sessions["procrastination_session"][1]["visits"] == ["visit-1"]
    assert store.visits[0]["url"] == "https://www.youtube.com/watch?v=demo"
