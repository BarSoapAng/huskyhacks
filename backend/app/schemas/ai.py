from pydantic import BaseModel, ConfigDict, Field


def to_camel(value: str) -> str:
    first, *rest = value.split("_")
    return first + "".join(part.capitalize() for part in rest)


class ApiModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )


class LearningCheckInput(ApiModel):
    url: str
    platform: str
    content_type: str = Field(alias="contentType")
    page_title: str | None = Field(default=None, alias="pageTitle")
    mock_transcript: str | None = Field(default=None, alias="mockTranscript")
    mock_page_description: str | None = Field(
        default=None,
        alias="mockPageDescription",
    )


class LearningCheckOutput(ApiModel):
    is_learning: bool = Field(alias="isLearning")
    confidence: float = Field(ge=0.0, le=1.0)
    reason: str
    detected_topic: str = Field(alias="detectedTopic")


class ProcrastinationScoreInput(ApiModel):
    url: str
    platform: str
    content_type: str = Field(alias="contentType")
    page_title: str | None = Field(default=None, alias="pageTitle")
    time_of_day: str | None = Field(default=None, alias="timeOfDay")
    recent_tab_sequence: list[str] = Field(default_factory=list, alias="recentTabSequence")
    session_duration_minutes: int | None = Field(
        default=None,
        alias="sessionDurationMinutes",
    )
    learning_check_result: LearningCheckOutput = Field(alias="learningCheckResult")


class ProcrastinationScoreOutput(ApiModel):
    procrastination_score: int = Field(ge=0, le=100, alias="procrastinationScore")
    confidence: float = Field(ge=0.0, le=1.0)
    reason: str
