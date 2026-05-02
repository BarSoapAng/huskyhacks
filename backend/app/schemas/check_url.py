from typing import Literal
from urllib.parse import urlparse

from pydantic import Field, field_validator

from app.schemas.ai import ApiModel


Platform = Literal["youtube", "instagram", "tiktok", "reddit", "twitter", "unknown"]
ContentType = Literal["shorts", "video", "feed", "profile", "search", "unknown"]
CheckUrlAction = Literal["allow", "soft_alert", "hard_block"]
CheckUrlSource = Literal[
    "safe_url",
    "learning_check",
    "procrastination_model",
    "debounce_pending",
]


class CheckUrlRequest(ApiModel):
    url: str = Field(min_length=1)
    page_title: str | None = Field(default=None, alias="pageTitle")
    mock_transcript: str | None = Field(default=None, alias="mockTranscript")
    mock_page_description: str | None = Field(
        default=None,
        alias="mockPageDescription",
    )
    recent_tab_sequence: list[str] = Field(default_factory=list, alias="recentTabSequence")
    session_duration_minutes: int | None = Field(
        default=None,
        ge=0,
        alias="sessionDurationMinutes",
    )
    time_of_day: str | None = Field(default=None, alias="timeOfDay")

    @field_validator("url")
    @classmethod
    def validate_url(cls, value: str) -> str:
        parsed = urlparse(value.strip())
        if not parsed.scheme:
            raise ValueError("url must be an absolute URL with a scheme")
        if parsed.scheme in {"http", "https"} and not parsed.netloc:
            raise ValueError("http and https URLs must include a hostname")
        return value.strip()


class NormalizedUrl(ApiModel):
    raw_url: str = Field(alias="rawUrl")
    hostname: str
    pathname: str
    query_params: dict[str, str] = Field(alias="queryParams")
    platform: Platform
    content_type: ContentType = Field(alias="contentType")


class CheckUrlResponse(ApiModel):
    allowed: bool
    action: CheckUrlAction
    procrastination_score: int | None = Field(alias="procrastinationScore")
    reason: str | None
    confidence: float | None
    source: CheckUrlSource
