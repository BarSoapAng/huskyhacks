from typing import Literal
from urllib.parse import urlparse

from pydantic import Field, StrictBool, field_validator

from app.schemas.ai import ApiModel


CreateSessionAction = Literal[
    "productive_session_active",
    "procrastination_session_active",
]
CreateSessionType = Literal["productive", "procrastination"]


class CreateSessionRequest(ApiModel):
    productive: StrictBool
    url: str = Field(min_length=1)
    page_title: str = Field(default="", alias="pageTitle")

    @field_validator("page_title", mode="before")
    @classmethod
    def normalize_page_title(cls, value: str | None) -> str:
        return "" if value is None else str(value)

    @field_validator("url")
    @classmethod
    def validate_url(cls, value: str) -> str:
        parsed = urlparse(value.strip())
        if not parsed.scheme:
            raise ValueError("url must be an absolute URL with a scheme")
        if parsed.scheme in {"http", "https"} and not parsed.netloc:
            raise ValueError("http and https URLs must include a hostname")
        return value.strip()


class CreateSessionResponse(ApiModel):
    success: bool
    action: CreateSessionAction
    session_type: CreateSessionType = Field(alias="sessionType")
    session_id: str | None = Field(default=None, alias="sessionId")
    reason: str
