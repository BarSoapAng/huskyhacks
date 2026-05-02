from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, status
from pydantic import ValidationError

from app.schemas.check_url import CheckUrlRequest, CheckUrlResponse
from app.services.gemini_client import (
    GeminiConfigurationError,
    GeminiGenerationError,
)
from app.services.supabase_browsing import (
    SupabaseBrowsingStore,
    get_anonymous_browsing_store,
    get_browsing_store,
)
from app.services.supabase_client import (
    AuthenticatedUser,
    SupabaseRequestError,
    get_current_user_optional,
)
from app.services.url_classifier import classify_url
from app.utils.normalize_url import normalize_url

router = APIRouter(prefix="/api", tags=["check-url"])

DEMO_USER2_DELAY_SECONDS = 30
_demo_user2_unsure_at: datetime | None = None
_demo_user2_productive_started = False


@router.post("/check-url", response_model=CheckUrlResponse)
async def check_url(
    payload: Any = Body(default=None),
    user: AuthenticatedUser | None = Depends(get_current_user_optional),
    store: SupabaseBrowsingStore = Depends(get_browsing_store),
) -> CheckUrlResponse:
    request = _validate_check_url_request(payload)

    if user is None:
        user = AuthenticatedUser(id="anonymous", access_token="anonymous")
        store = get_anonymous_browsing_store()

    try:
        return await classify_url(request, user=user, store=store)
    except GeminiConfigurationError as exc:
        return CheckUrlResponse(
            allowed=True,
            action="ask_user",
            sessionType=None,
            reason=str(exc),
            classification="unsure",
            confidence=None,
        )
    except GeminiGenerationError as exc:
        return CheckUrlResponse(
            allowed=True,
            action="ask_user",
            sessionType=None,
            reason=str(exc),
            classification="unsure",
            confidence=None,
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
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Supabase request failed.",
        ) from exc


@router.post("/demo_check_url_user1", response_model=CheckUrlResponse)
async def demo_check_url_user1(
    payload: Any = Body(default=None),
) -> CheckUrlResponse:
    request = _validate_check_url_request(payload)
    now = _current_demo_datetime()

    if _is_youtube_url(request):
        if _is_hour(now, 17):
            return CheckUrlResponse(
                allowed=True,
                action="continue",
                sessionType="allowed",
                reason="You're typically taking a break at this time :)",
                classification="okay",
                confidence=0.93,
            )

        if _is_hour(now, 20):
            return CheckUrlResponse(
                allowed=False,
                action="hard_ban",
                sessionType="procrastination",
                reason="You seem to be working on a hardware project",
                classification="bad",
                confidence=0.97,
            )

    return CheckUrlResponse(
        allowed=True,
        action="continue",
        sessionType="allowed",
        reason="This link is productive!",
        classification="good",
        confidence=1.0,
    )


@router.post("/demo_check_url_user2", response_model=CheckUrlResponse)
async def demo_check_url_user2(
    payload: Any = Body(default=None),
) -> CheckUrlResponse:
    global _demo_user2_productive_started, _demo_user2_unsure_at

    request = _validate_check_url_request(payload)
    now = _current_demo_datetime()

    if _is_youtube_url(request) and _is_hour(now, 17):
        if _demo_user2_productive_started:
            return CheckUrlResponse(
                allowed=True,
                action="continue",
                sessionType="productive",
                reason="Demo user 2: Productive session is already active.",
                classification="good",
                confidence=1.0,
            )

        if _demo_user2_unsure_at is None:
            _demo_user2_unsure_at = now
            return _demo_user2_unsure_response()

        if now - _demo_user2_unsure_at >= timedelta(
            seconds=DEMO_USER2_DELAY_SECONDS,
        ):
            _demo_user2_productive_started = True
            _demo_user2_unsure_at = None
            return CheckUrlResponse(
                allowed=True,
                action="productive_started",
                sessionType="productive",
                reason=(
                    "Demo user 2: 30 seconds elapsed, so a productive session "
                    "has started."
                ),
                classification="good",
                confidence=1.0,
            )

        return _demo_user2_unsure_response()

    _reset_demo_user2_state()
    return CheckUrlResponse(
        allowed=True,
        action="continue",
        sessionType="allowed",
        reason="Demo user 2: URL is allowed by demo rules.",
        classification="good",
        confidence=1.0,
    )


def _validate_check_url_request(payload: Any) -> CheckUrlRequest:
    try:
        return CheckUrlRequest.model_validate(payload)
    except ValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=[
                {
                    "loc": error["loc"],
                    "msg": error["msg"],
                    "type": error["type"],
                }
                for error in exc.errors()
            ],
        ) from exc


def _current_demo_datetime() -> datetime:
    return datetime.now().astimezone()


def _is_youtube_url(request: CheckUrlRequest) -> bool:
    return normalize_url(request.url).platform == "youtube"


def _is_hour(value: datetime, hour: int) -> bool:
    return value.hour == hour


def _demo_user2_unsure_response() -> CheckUrlResponse:
    return CheckUrlResponse(
        allowed=True,
        action="ask_user",
        sessionType=None,
        reason="I'm not quite sure what you're working on",
        classification="unsure",
        confidence=0.35,
    )


def _reset_demo_user2_state() -> None:
    global _demo_user2_productive_started, _demo_user2_unsure_at

    _demo_user2_unsure_at = None
    _demo_user2_productive_started = False
