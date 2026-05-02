from typing import Any, Literal

from app.schemas.ai import ApiModel


SessionVisualizationType = Literal["productive", "procrastination", "allowed"]


class SessionVisualizationSession(ApiModel):
    id: str
    type: SessionVisualizationType
    timestamp: str
    active: bool
    duration: float
    visit_count: int | None = None
    visits: list[Any] | None = None


class SessionVisualizationVisit(ApiModel):
    id: str
    timestamp: str
    duration: float
    url: str
    page_title: str


class SessionVisualizationResponse(ApiModel):
    sessions: list[SessionVisualizationSession]
    visits: list[SessionVisualizationVisit]
