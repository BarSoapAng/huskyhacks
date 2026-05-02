import pytest

from app.core.settings import get_settings
from app.schemas.ai import LearningCheckInput, ProcrastinationScoreInput
from app.services.ai_learning_check import ai_learning_check
from app.services.ai_procrastination_score import ai_procrastination_score


pytestmark = pytest.mark.anyio


def _requires_gemini_key() -> None:
    if not get_settings().gemini_api_key:
        pytest.skip("GEMINI_API_KEY is not configured.")


async def test_ai_learning_check_uses_real_gemini() -> None:
    _requires_gemini_key()

    result = await ai_learning_check(
        LearningCheckInput(
            url="https://youtube.com/watch?v=control-systems-lesson",
            platform="youtube",
            contentType="video",
            pageTitle="Laplace Transform Examples for Control Systems",
            mockPageDescription="Educational engineering lesson with worked examples.",
        )
    )

    assert isinstance(result.is_learning, bool)
    assert 0 <= result.confidence <= 1
    assert result.reason
    assert result.detected_topic


async def test_ai_procrastination_score_uses_real_gemini() -> None:
    _requires_gemini_key()

    learning_result = await ai_learning_check(
        LearningCheckInput(
            url="https://youtube.com/shorts/funny-fails",
            platform="youtube",
            contentType="shorts",
            pageTitle="Funny fails compilation",
            mockPageDescription="Short-form entertainment video.",
        )
    )
    result = await ai_procrastination_score(
        ProcrastinationScoreInput(
            url="https://youtube.com/shorts/funny-fails",
            platform="youtube",
            contentType="shorts",
            pageTitle="Funny fails compilation",
            recentTabSequence=[
                "https://learn.uwaterloo.ca/control-systems-assignment",
                "https://youtube.com/results?search_query=pid+controller",
            ],
            sessionDurationMinutes=12,
            learningCheckResult=learning_result,
        )
    )

    assert 0 <= result.procrastination_score <= 100
    assert 0 <= result.confidence <= 1
    assert result.reason
