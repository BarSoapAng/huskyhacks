from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, status
from pydantic import ValidationError

from app.schemas.check_url import CheckUrlRequest, CheckUrlResponse
from app.services.gemini_client import (
    GeminiConfigurationError,
    GeminiGenerationError,
)
from app.services.supabase_browsing import SupabaseBrowsingStore, get_browsing_store
from app.services.supabase_client import (
    AuthenticatedUser,
    SupabaseRequestError,
    get_current_user,
)
from app.services.url_classifier import classify_url

router = APIRouter(prefix="/api", tags=["check-url"])


@router.post("/check-url", response_model=CheckUrlResponse)
async def check_url(
    payload: Any = Body(default=None),
    user: AuthenticatedUser = Depends(get_current_user),
    store: SupabaseBrowsingStore = Depends(get_browsing_store),
) -> CheckUrlResponse:
    try:
        request = CheckUrlRequest.model_validate(payload)
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
