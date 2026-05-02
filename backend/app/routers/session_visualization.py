from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, status
from fastapi.responses import JSONResponse

from app.core.settings import Settings, get_settings
from app.schemas.session_visualization import (
    SessionVisualizationResponse,
    SessionVisualizationSession,
    SessionVisualizationType,
    SessionVisualizationVisit,
)
from app.services.supabase_browsing import (
    SessionTable,
    SupabaseBrowsingStore,
    get_browsing_store,
)
from app.services.supabase_client import (
    AuthenticatedUser,
    SupabaseConfigurationError,
    SupabaseRequestError,
    SupabaseRestClient,
    get_supabase_rest_client,
)

router = APIRouter(prefix="/api", tags=["session-visualization"])

SESSION_LIMIT = 20
VISIT_LIMIT = 30

SESSION_TABLES: tuple[tuple[SessionTable, SessionVisualizationType], ...] = (
    ("productive_session", "productive"),
    ("procrastination_session", "procrastination"),
    ("allowed_sessions", "allowed"),
)


@router.get(
    "/session-visualization",
    response_model=SessionVisualizationResponse,
)
async def session_visualization(
    authorization: str | None = Header(default=None, alias="Authorization"),
    store: SupabaseBrowsingStore = Depends(get_browsing_store),
) -> SessionVisualizationResponse | JSONResponse:
    try:
        user, store = await _get_activity_source(authorization, store)
        sessions: list[SessionVisualizationSession] = []
        for table, session_type in SESSION_TABLES:
            rows = await store.list_recent_sessions(user, table, limit=SESSION_LIMIT)
            sessions.extend(
                _normalize_session(row, session_type)
                for row in rows
                if row.get("id") is not None
            )

        sessions.sort(
            key=lambda session: _timestamp_sort_key(session.timestamp),
            reverse=True,
        )
        visits = await store.list_recent_visits(user, limit=VISIT_LIMIT)

        return SessionVisualizationResponse(
            sessions=sessions[:SESSION_LIMIT],
            visits=[
                _normalize_visit(row)
                for row in visits
                if row.get("id") is not None
            ],
        )
    except SupabaseRequestError as exc:
        if exc.status_code in {
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        }:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid Supabase session.",
            ) from exc

        return _error_response(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "INTERNAL_ERROR",
            "Unable to load session visualization data.",
        )
    except SupabaseConfigurationError:
        return _error_response(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "INTERNAL_ERROR",
            "Unable to load session visualization data.",
        )


async def _get_activity_source(
    authorization: str | None,
    store: SupabaseBrowsingStore,
) -> tuple[AuthenticatedUser, SupabaseBrowsingStore]:
    access_token = _extract_bearer_token(authorization)
    if access_token:
        user = await get_supabase_rest_client().get_user(access_token)
        return user, store

    if not isinstance(store, SupabaseBrowsingStore):
        return AuthenticatedUser(id="", access_token=""), store

    settings = get_settings()
    if settings.supabase_secret_key:
        return _local_backend_source(settings)

    return AuthenticatedUser(id="", access_token=""), store


def _local_backend_source(
    settings: Settings,
) -> tuple[AuthenticatedUser, SupabaseBrowsingStore]:
    client = SupabaseRestClient(
        Settings(
            gemini_api_key=settings.gemini_api_key,
            gemini_model=settings.gemini_model,
            supabase_url=settings.supabase_url,
            supabase_publishable_key=settings.supabase_secret_key,
            supabase_secret_key=settings.supabase_secret_key,
        )
    )
    user = AuthenticatedUser(id="", access_token=settings.supabase_secret_key or "")
    return user, SupabaseBrowsingStore(client)


def _extract_bearer_token(authorization: str | None) -> str | None:
    if not authorization:
        return None

    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        return None

    return token.strip()


def _normalize_session(
    row: dict[str, Any],
    session_type: SessionVisualizationType,
) -> SessionVisualizationSession:
    visits = row.get("visits")
    normalized_visits = visits if isinstance(visits, list) else None

    return SessionVisualizationSession(
        id=str(row["id"]),
        type=session_type,
        timestamp=_format_timestamp(row.get("timestamp")),
        active=bool(row.get("active")),
        duration=_number(row.get("duration")),
        visitCount=len(normalized_visits) if normalized_visits is not None else None,
        visits=normalized_visits,
    )


def _normalize_visit(row: dict[str, Any]) -> SessionVisualizationVisit:
    return SessionVisualizationVisit(
        id=str(row["id"]),
        timestamp=_format_timestamp(row.get("timestamp")),
        duration=_number(row.get("duration")),
        url=str(row.get("url") or ""),
        pageTitle=str(row.get("page_title") or ""),
    )


def _format_timestamp(value: Any) -> str:
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str):
        return value
    else:
        return ""

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)

    return parsed.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _timestamp_sort_key(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return datetime.min.replace(tzinfo=UTC)

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)

    return parsed.astimezone(UTC)


def _number(value: Any) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _error_response(status_code: int, error: str, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "error": error,
            "message": message,
        },
    )
