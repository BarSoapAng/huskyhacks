from fastapi import APIRouter, HTTPException, status

from app.schemas.check_url import CheckUrlRequest, CheckUrlResponse
from app.services.gemini_client import (
    GeminiConfigurationError,
    GeminiGenerationError,
)
from app.services.url_classifier import classify_url

router = APIRouter(prefix="/api", tags=["check-url"])


@router.post("/check-url", response_model=CheckUrlResponse)
async def check_url(request: CheckUrlRequest) -> CheckUrlResponse:
    try:
        return await classify_url(request)
    except GeminiConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except GeminiGenerationError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc
