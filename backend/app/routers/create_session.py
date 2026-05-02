from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from app.schemas.check_url import CheckUrlRequest
from app.schemas.create_session import CreateSessionRequest, CreateSessionResponse
from app.services.supabase_browsing import (
    SessionTable,
    SupabaseBrowsingStore,
    get_browsing_store,
)
from app.services.supabase_client import (
    AuthenticatedUser,
    SupabaseRequestError,
    get_current_user,
)
from app.services.url_classifier import (
    end_active_session,
    extend_active_session,
    get_or_create_current_visit,
)
from app.utils.normalize_url import normalize_url

router = APIRouter(prefix="/api", tags=["create-session"])


@router.post("/create-session", response_model=CreateSessionResponse)
async def create_session(
    payload: Any = Body(default=None),
    user: AuthenticatedUser = Depends(get_current_user),
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
    normalized = normalize_url(request.url)
    check_url_request = CheckUrlRequest(
        url=request.url,
        pageTitle=request.page_title,
    )

    try:
        visit, elapsed_seconds = await get_or_create_current_visit(
            request=check_url_request,
            normalized=normalized,
            user=user,
            store=store,
            now=now,
        )

        if request.productive:
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


def _error_response(status_code: int, error: str, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "error": error,
            "message": message,
        },
    )
