from typing import Literal
from urllib.parse import urlparse

from pydantic import Field, StrictBool, field_validator, model_validator

from app.schemas.ai import ApiModel


CreateSessionAction = Literal[
    "productive_session_active",
    "procrastination_session_active",
    "allowed_session_active",
]
CreateSessionType = Literal["productive", "procrastination", "allowed"]


class CreateSessionRequest(ApiModel):
    productive: StrictBool | None = None
    session_type: CreateSessionType | None = Field(default=None, alias="sessionType")
    url: str | None = Field(default=None, min_length=1)
    page_title: str = Field(default="", alias="pageTitle")

    @model_validator(mode="after")
    def validate_session_request(self) -> "CreateSessionRequest":
        if self.session_type is None and self.productive is None:
            raise ValueError("sessionType or productive is required")

        if self.resolved_session_type != "allowed" and self.url is None:
            raise ValueError("url is required")

        return self

    @property
    def resolved_session_type(self) -> CreateSessionType:
        if self.session_type is not None:
            return self.session_type

        return "productive" if self.productive else "procrastination"

    @field_validator("page_title", mode="before")
    @classmethod
    def normalize_page_title(cls, value: str | None) -> str:
        return "" if value is None else str(value)

    @field_validator("url")
    @classmethod
    def validate_url(cls, value: str | None) -> str | None:
        if value is None:
            return None

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
