from datetime import UTC, datetime
from typing import Any, Literal

from app.services.supabase_client import AuthenticatedUser, SupabaseRestClient


SessionTable = Literal[
    "procrastination_session",
    "productive_session",
    "allowed_sessions",
]


class SupabaseBrowsingStore:
    def __init__(self, client: SupabaseRestClient) -> None:
        self._client = client

    async def list_bad_domains(self, user: AuthenticatedUser) -> list[str]:
        rows = await self._client.request(
            "GET",
            "/rest/v1/bad_domains",
            access_token=user.access_token,
            query={"select": "url", "order": "url.asc"},
        )
        return [row["url"] for row in rows if row.get("url")]

    async def get_latest_visit(
        self,
        user: AuthenticatedUser,
    ) -> dict[str, Any] | None:
        rows = await self._client.request(
            "GET",
            "/rest/v1/visits",
            access_token=user.access_token,
            query={
                "select": "*",
                "user_id": f"eq.{user.id}",
                "order": "last_seen_at.desc",
                "limit": "1",
            },
        )
        return _first_row(rows)

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
        rows = await self._client.request(
            "POST",
            "/rest/v1/visits",
            access_token=user.access_token,
            json_body={
                "user_id": user.id,
                "timestamp": _format_datetime(now),
                "duration": 0,
                "url": url,
                "normalized_url": normalized_url,
                "domain": domain,
                "page_title": page_title,
                "last_seen_at": _format_datetime(now),
            },
            prefer="return=representation",
        )
        return _first_row(rows) or {}

    async def update_visit(
        self,
        user: AuthenticatedUser,
        visit: dict[str, Any],
        *,
        duration: float,
        page_title: str,
        now: datetime,
    ) -> dict[str, Any]:
        rows = await self._client.request(
            "PATCH",
            "/rest/v1/visits",
            access_token=user.access_token,
            query={
                "id": f"eq.{visit['id']}",
                "user_id": f"eq.{user.id}",
            },
            json_body={
                "duration": duration,
                "page_title": page_title,
                "last_seen_at": _format_datetime(now),
            },
            prefer="return=representation",
        )
        return _first_row(rows) or {**visit, "duration": duration}

    async def list_recent_visits(
        self,
        user: AuthenticatedUser,
        *,
        limit: int,
    ) -> list[dict[str, Any]]:
        query = {
            "select": "id,user_id,timestamp,duration,url,page_title",
            "order": "timestamp.desc",
            "limit": str(limit),
        }
        if user.id:
            query["user_id"] = f"eq.{user.id}"

        rows = await self._client.request(
            "GET",
            "/rest/v1/visits",
            access_token=user.access_token,
            query=query,
        )
        return rows if isinstance(rows, list) else []

    async def get_active_session(
        self,
        user: AuthenticatedUser,
        table: SessionTable,
    ) -> dict[str, Any] | None:
        rows = await self._client.request(
            "GET",
            f"/rest/v1/{table}",
            access_token=user.access_token,
            query={
                "select": "*",
                "user_id": f"eq.{user.id}",
                "active": "eq.true",
                "order": "timestamp.desc",
                "limit": "1",
            },
        )
        return _first_row(rows)

    async def list_recent_sessions(
        self,
        user: AuthenticatedUser,
        table: SessionTable,
        *,
        limit: int,
    ) -> list[dict[str, Any]]:
        query = {
            "select": "id,timestamp,active,duration,visits",
            "order": "timestamp.desc",
            "limit": str(limit),
        }
        if user.id:
            query["user_id"] = f"eq.{user.id}"

        rows = await self._client.request(
            "GET",
            f"/rest/v1/{table}",
            access_token=user.access_token,
            query=query,
        )
        return rows if isinstance(rows, list) else []

    async def create_session(
        self,
        user: AuthenticatedUser,
        table: SessionTable,
        *,
        visit_id: str,
        now: datetime,
        duration: float = 0,
    ) -> dict[str, Any]:
        rows = await self._client.request(
            "POST",
            f"/rest/v1/{table}",
            access_token=user.access_token,
            json_body={
                "user_id": user.id,
                "timestamp": _format_datetime(now),
                "active": True,
                "duration": duration,
                "visits": [visit_id],
            },
            prefer="return=representation",
        )
        return _first_row(rows) or {}

    async def update_session(
        self,
        user: AuthenticatedUser,
        table: SessionTable,
        session: dict[str, Any],
        updates: dict[str, Any],
    ) -> dict[str, Any]:
        rows = await self._client.request(
            "PATCH",
            f"/rest/v1/{table}",
            access_token=user.access_token,
            query={
                "id": f"eq.{session['id']}",
                "user_id": f"eq.{user.id}",
            },
            json_body=updates,
            prefer="return=representation",
        )
        return _first_row(rows) or {**session, **updates}


def get_browsing_store() -> SupabaseBrowsingStore:
    from app.services.supabase_client import get_supabase_rest_client

    return SupabaseBrowsingStore(get_supabase_rest_client())


class AnonymousBrowsingStore:
    def __init__(self):
        # Simple in-memory storage for anonymous user
        self._visits: dict[str, dict[str, Any]] = {}
        self._sessions: dict[str, dict[str, Any]] = {}

    async def list_bad_domains(self, user: AuthenticatedUser) -> list[str]:
        return []

    async def get_latest_visit(
        self,
        user: AuthenticatedUser,
    ) -> dict[str, Any] | None:
        # Return the most recent visit for this user
        visits = [v for v in self._visits.values() if v.get("user_id") == user.id]
        if not visits:
            return None
        return max(visits, key=lambda v: v.get("last_seen_at", ""))

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
        visit_id = f"anon-visit-{len(self._visits) + 1}"
        visit = {
            "id": visit_id,
            "user_id": user.id,
            "url": url,
            "normalized_url": normalized_url,
            "domain": domain,
            "page_title": page_title,
            "duration": 0,
            "last_seen_at": _format_datetime(now),
            "timestamp": _format_datetime(now),
        }
        self._visits[visit_id] = visit
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
        visit_id = visit["id"]
        if visit_id in self._visits:
            self._visits[visit_id].update({
                "duration": duration,
                "page_title": page_title,
                "last_seen_at": _format_datetime(now),
            })
        return self._visits[visit_id]

    async def get_active_session(
        self,
        user: AuthenticatedUser,
        table: SessionTable,
    ) -> dict[str, Any] | None:
        session_key = f"{user.id}-{table}"
        session = self._sessions.get(session_key)
        if session and session.get("active"):
            return session
        return None

    async def create_session(
        self,
        user: AuthenticatedUser,
        table: SessionTable,
        *,
        visit_id: str,
        now: datetime,
        duration: float = 0,
    ) -> dict[str, Any]:
        session_key = f"{user.id}-{table}"
        session = {
            "id": f"anon-session-{table}-{len(self._sessions) + 1}",
            "user_id": user.id,
            "active": True,
            "duration": duration,
            "visits": [visit_id],
            "timestamp": _format_datetime(now),
        }
        self._sessions[session_key] = session
        return session

    async def update_session(
        self,
        user: AuthenticatedUser,
        table: SessionTable,
        session: dict[str, Any],
        updates: dict[str, Any],
    ) -> dict[str, Any]:
        session_key = f"{user.id}-{table}"
        if session_key in self._sessions:
            self._sessions[session_key].update(updates)
        return self._sessions[session_key]


def get_anonymous_browsing_store() -> AnonymousBrowsingStore:
    # Return a singleton instance to persist state across requests
    if not hasattr(get_anonymous_browsing_store, "_instance"):
        get_anonymous_browsing_store._instance = AnonymousBrowsingStore()
    return get_anonymous_browsing_store._instance


def append_visit_id(session: dict[str, Any], visit_id: str) -> list[str]:
    visits = list(session.get("visits") or [])
    if visit_id not in visits:
        visits.append(visit_id)
    return visits


def _first_row(rows: Any) -> dict[str, Any] | None:
    if isinstance(rows, list) and rows:
        return rows[0]
    return None


def _format_datetime(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")
