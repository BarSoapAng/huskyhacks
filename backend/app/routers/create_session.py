from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Body, Depends, Header, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from app.core.settings import Settings, get_settings
from app.schemas.check_url import CheckUrlRequest
from app.schemas.create_session import (
    CreateSessionRequest,
    CreateSessionResponse,
    CreateSessionType,
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
from app.services.url_classifier import (
    end_active_session,
    extend_active_session,
    get_or_create_current_visit,
)
from app.utils.normalize_url import normalize_url

router = APIRouter(prefix="/api", tags=["create-session"])

LOCAL_DEMO_USER_ID = "11111111-1111-4111-8111-111111111111"


async def get_create_session_user(
    authorization: str | None = Header(default=None, alias="Authorization"),
) -> AuthenticatedUser | None:
    access_token = _extract_bearer_token(authorization)
    if not access_token:
        return None

    try:
        return await get_supabase_rest_client().get_user(access_token)
    except SupabaseConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except SupabaseRequestError as exc:
        if exc.status_code in {
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        }:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid Supabase session.",
            ) from exc

        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Supabase request failed.",
        ) from exc


@router.post("/create-session", response_model=CreateSessionResponse)
async def create_session(
    payload: Any = Body(default=None),
    current_user: AuthenticatedUser | None = Depends(get_create_session_user),
    store: SupabaseBrowsingStore = Depends(get_browsing_store),
) -> CreateSessionResponse | JSONResponse:
    try:
        request = CreateSessionRequest.model_validate(payload)
    except ValidationError:
        return _error_response(
            status.HTTP_400_BAD_REQUEST,
            "INVALID_REQUEST",
            "productive must be a boolean and url must be valid.",
        )

    now = datetime.now(UTC)

    try:
        user, store = _get_create_session_source(
            request.resolved_session_type,
            current_user,
            store,
        )

        if request.resolved_session_type == "allowed":
            return await _activate_allowed_session(
                user=user,
                store=store,
                request=request,
                now=now,
            )

        url = request.url or ""
        normalized = normalize_url(url)
        check_url_request = CheckUrlRequest(
            url=url,
            pageTitle=request.page_title,
        )
        visit, elapsed_seconds = await get_or_create_current_visit(
            request=check_url_request,
            normalized=normalized,
            user=user,
            store=store,
            now=now,
        )

        if request.resolved_session_type == "productive":
            return await _activate_productive_session(
                user=user,
                store=store,
                visit=visit,
                elapsed_seconds=elapsed_seconds,
                now=now,
            )

        return await _activate_procrastination_session(
            user=user,
            store=store,
            visit=visit,
            elapsed_seconds=elapsed_seconds,
            now=now,
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
            "Unable to create session.",
        )
    except SupabaseConfigurationError:
        return _error_response(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "INTERNAL_ERROR",
            "Unable to create session.",
        )


@router.post(
    "/demo/mark-current-session-unproductive",
    response_model=CreateSessionResponse,
)
async def mark_current_session_unproductive(
    payload: Any = Body(default=None),
    store: SupabaseBrowsingStore = Depends(get_browsing_store),
) -> CreateSessionResponse | JSONResponse:
    try:
        request = CreateSessionRequest.model_validate(
            {
                **(payload if isinstance(payload, dict) else {}),
                "sessionType": "procrastination",
            }
        )
    except ValidationError:
        return _error_response(
            status.HTTP_400_BAD_REQUEST,
            "INVALID_REQUEST",
            "url must be valid.",
        )

    now = datetime.now(UTC)

    try:
        user, store = _get_local_demo_source(store)
        normalized = normalize_url(request.url or "")
        check_url_request = CheckUrlRequest(
            url=request.url or "",
            pageTitle=request.page_title,
        )
        visit, elapsed_seconds = await get_or_create_current_visit(
            request=check_url_request,
            normalized=normalized,
            user=user,
            store=store,
            now=now,
        )

        await _deactivate_latest_session(user, store, "productive_session")
        await _deactivate_active_session(user, store, "procrastination_session")

        session = await _start_session(
            user,
            store,
            "procrastination_session",
            visit,
            now,
            elapsed_seconds,
        )
        return CreateSessionResponse(
            success=True,
            action="procrastination_session_active",
            sessionType="procrastination",
            sessionId=_session_id(session),
            reason="Current session marked as unproductive.",
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
            "Unable to mark session as unproductive.",
        )
    except SupabaseConfigurationError:
        return _error_response(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "INTERNAL_ERROR",
            "Unable to mark session as unproductive.",
        )


async def _activate_productive_session(
    *,
    user: AuthenticatedUser,
    store: SupabaseBrowsingStore,
    visit: dict[str, Any],
    elapsed_seconds: float,
    now: datetime,
) -> CreateSessionResponse:
    session = await store.get_active_session(user, "productive_session")
    if session:
        session = await extend_active_session(
            user,
            store,
            "productive_session",
            session,
            visit,
            elapsed_seconds,
        )
        return CreateSessionResponse(
            success=True,
            action="productive_session_active",
            sessionType="productive",
            sessionId=_session_id(session),
            reason="Existing productive session continued.",
        )

    procrastination_session = await store.get_active_session(
        user,
        "procrastination_session",
    )
    if procrastination_session:
        await end_active_session(
            user,
            store,
            "procrastination_session",
            procrastination_session,
        )
        reason = "Procrastination session ended and productive session started."
    else:
        reason = "Productive session started."

    session = await _start_session(
        user,
        store,
        "productive_session",
        visit,
        now,
        elapsed_seconds,
    )
    return CreateSessionResponse(
        success=True,
        action="productive_session_active",
        sessionType="productive",
        sessionId=_session_id(session),
        reason=reason,
    )


async def _activate_procrastination_session(
    *,
    user: AuthenticatedUser,
    store: SupabaseBrowsingStore,
    visit: dict[str, Any],
    elapsed_seconds: float,
    now: datetime,
) -> CreateSessionResponse:
    session = await store.get_active_session(user, "procrastination_session")
    if session:
        session = await extend_active_session(
            user,
            store,
            "procrastination_session",
            session,
            visit,
            elapsed_seconds,
        )
        return CreateSessionResponse(
            success=True,
            action="procrastination_session_active",
            sessionType="procrastination",
            sessionId=_session_id(session),
            reason="Existing procrastination session continued.",
        )

    productive_session = await store.get_active_session(user, "productive_session")
    if productive_session:
        await end_active_session(
            user,
            store,
            "productive_session",
            productive_session,
        )
        reason = "Productive session ended and procrastination session started."
    else:
        reason = "Procrastination session started."

    session = await _start_session(
        user,
        store,
        "procrastination_session",
        visit,
        now,
        elapsed_seconds,
    )
    return CreateSessionResponse(
        success=True,
        action="procrastination_session_active",
        sessionType="procrastination",
        sessionId=_session_id(session),
        reason=reason,
    )


async def _activate_allowed_session(
    *,
    user: AuthenticatedUser,
    store: SupabaseBrowsingStore,
    request: CreateSessionRequest,
    now: datetime,
) -> CreateSessionResponse:
    if request.url and user.id:
        normalized = normalize_url(request.url)
        check_url_request = CheckUrlRequest(
            url=request.url,
            pageTitle=request.page_title,
        )
        visit, elapsed_seconds = await get_or_create_current_visit(
            request=check_url_request,
            normalized=normalized,
            user=user,
            store=store,
            now=now,
        )
    else:
        visit = await _get_latest_visit_for_allowed_session(user, store)
        elapsed_seconds = 0.0
        user = AuthenticatedUser(
            id=str(visit.get("user_id") or user.id),
            access_token=user.access_token,
        )

    await end_active_session(user, store, "procrastination_session")
    session = await store.get_active_session(user, "allowed_sessions")
    if session:
        session = await extend_active_session(
            user,
            store,
            "allowed_sessions",
            session,
            visit,
            elapsed_seconds,
        )
        reason = "Existing allowed session continued."
    else:
        session = await _start_session(
            user,
            store,
            "allowed_sessions",
            visit,
            now,
            elapsed_seconds,
        )
        reason = "Current session marked as allowed."

    return CreateSessionResponse(
        success=True,
        action="allowed_session_active",
        sessionType="allowed",
        sessionId=_session_id(session),
        reason=reason,
    )


async def _get_latest_visit_for_allowed_session(
    user: AuthenticatedUser,
    store: SupabaseBrowsingStore,
) -> dict[str, Any]:
    if user.id:
        visit = await store.get_latest_visit(user)
        if visit:
            return visit

    visits = await store.list_recent_visits(user, limit=1)
    if visits:
        return visits[0]

    raise SupabaseRequestError(
        status.HTTP_404_NOT_FOUND,
        "No visits found for allowed session.",
    )


def _session_id(session: dict[str, Any]) -> str | None:
    session_id = session.get("id")
    return str(session_id) if session_id is not None else None


async def _start_session(
    user: AuthenticatedUser,
    store: SupabaseBrowsingStore,
    table: SessionTable,
    visit: dict[str, Any],
    now: datetime,
    duration: float,
) -> dict[str, Any]:
    return await store.create_session(
        user,
        table,
        visit_id=visit["id"],
        now=now,
        duration=duration,
    )


def _get_local_demo_source(
    store: SupabaseBrowsingStore,
) -> tuple[AuthenticatedUser, SupabaseBrowsingStore]:
    if not isinstance(store, SupabaseBrowsingStore):
        return AuthenticatedUser(id=LOCAL_DEMO_USER_ID, access_token="local-demo"), store

    settings = get_settings()
    if not settings.supabase_secret_key:
        raise SupabaseConfigurationError("SUPABASE_SECRET_KEY is not configured.")

    return _local_backend_source(settings, user_id=LOCAL_DEMO_USER_ID)


def _get_create_session_source(
    session_type: CreateSessionType,
    current_user: AuthenticatedUser | None,
    store: SupabaseBrowsingStore,
) -> tuple[AuthenticatedUser, SupabaseBrowsingStore]:
    if current_user is not None:
        return current_user, store

    if session_type != "allowed":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Supabase session.",
        )

    if not isinstance(store, SupabaseBrowsingStore):
        return AuthenticatedUser(id="", access_token=""), store

    settings = get_settings()
    if not settings.supabase_secret_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Supabase session.",
        )

    return _local_backend_source(settings)


def _local_backend_source(
    settings: Settings,
    *,
    user_id: str = "",
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
    return (
        AuthenticatedUser(id=user_id, access_token=settings.supabase_secret_key or ""),
        SupabaseBrowsingStore(client),
    )


async def _deactivate_latest_session(
    user: AuthenticatedUser,
    store: SupabaseBrowsingStore,
    table: SessionTable,
) -> None:
    sessions = await store.list_recent_sessions(user, table, limit=1)
    if sessions:
        await store.update_session(user, table, sessions[0], {"active": False})


async def _deactivate_active_session(
    user: AuthenticatedUser,
    store: SupabaseBrowsingStore,
    table: SessionTable,
) -> None:
    session = await store.get_active_session(user, table)
    if session:
        await store.update_session(user, table, session, {"active": False})


def _extract_bearer_token(authorization: str | None) -> str | None:
    if not authorization:
        return None

    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        return None

    return token.strip()


def _error_response(status_code: int, error: str, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "error": error,
            "message": message,
        },
    )
