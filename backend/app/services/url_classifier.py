from app.config.bad_links import BAD_LINK_RULES, BadLinkRule
from app.schemas.ai import (
    LearningCheckInput,
    LearningCheckOutput,
    ProcrastinationScoreInput,
)
from app.schemas.check_url import (
    CheckUrlAction,
    CheckUrlRequest,
    CheckUrlResponse,
    NormalizedUrl,
)
from app.services.ai_learning_check import ai_learning_check
from app.services.ai_procrastination_score import ai_procrastination_score
from app.services.debounce import debounce_service
from app.utils.normalize_url import build_debounce_url_key, normalize_url


MOCK_USER_CONTEXT = {
    "timeOfDay": "21:30",
    "recentTabSequence": [
        "https://learn.uwaterloo.ca/control-systems-assignment",
        "https://youtube.com/results?search_query=pid+controller",
        "https://youtube.com/shorts/xyz",
    ],
    "sessionDurationMinutes": 12,
}


async def classify_url(request: CheckUrlRequest) -> CheckUrlResponse:
    normalized = normalize_url(request.url)
    bad_link_rule = find_bad_link_rule(normalized)

    if bad_link_rule is None:
        return CheckUrlResponse(
            allowed=True,
            action="allow",
            procrastinationScore=None,
            reason=None,
            confidence=None,
            source="safe_url",
        )

    debounce_key = build_debounce_url_key(normalized)
    debounce_status = debounce_service.check(debounce_key)

    if debounce_status == "started":
        return CheckUrlResponse(
            allowed=True,
            action="allow",
            procrastinationScore=None,
            reason="Debounce started for potentially distracting URL.",
            confidence=None,
            source="debounce_pending",
        )

    if debounce_status == "pending":
        return CheckUrlResponse(
            allowed=True,
            action="allow",
            procrastinationScore=None,
            reason="Debounce still pending.",
            confidence=None,
            source="debounce_pending",
        )

    learning_input = build_learning_input(request, normalized)
    learning_result = await ai_learning_check(learning_input)

    if learning_result.is_learning and learning_result.confidence >= 0.75:
        return CheckUrlResponse(
            allowed=True,
            action="allow",
            procrastinationScore=15,
            reason=learning_result.reason,
            confidence=learning_result.confidence,
            source="learning_check",
        )

    procrastination_input = build_procrastination_input(
        request=request,
        normalized=normalized,
        learning_result=learning_result,
    )
    procrastination_result = await ai_procrastination_score(procrastination_input)
    mapped = map_score_to_action(
        procrastination_result.procrastination_score,
        procrastination_result.confidence,
    )

    return CheckUrlResponse(
        allowed=mapped["allowed"],
        action=mapped["action"],
        procrastinationScore=procrastination_result.procrastination_score,
        reason=procrastination_result.reason,
        confidence=procrastination_result.confidence,
        source="procrastination_model",
    )


def find_bad_link_rule(normalized: NormalizedUrl) -> BadLinkRule | None:
    for rule in BAD_LINK_RULES:
        if any(_matches_rule(normalized, match) for match in rule.matches):
            return rule
    return None


def _matches_rule(normalized: NormalizedUrl, match: str) -> bool:
    host, _, path = match.partition("/")
    host_matches = (
        normalized.hostname == host
        or normalized.hostname.endswith(f".{host}")
    )

    if not host_matches:
        return False

    if not path:
        return True

    return normalized.pathname.lower().startswith(f"/{path}")


def build_learning_input(
    request: CheckUrlRequest,
    normalized: NormalizedUrl,
) -> LearningCheckInput:
    return LearningCheckInput(
        url=normalized.raw_url,
        platform=normalized.platform,
        contentType=normalized.content_type,
        pageTitle=request.page_title,
        mockTranscript=request.mock_transcript,
        mockPageDescription=request.mock_page_description,
    )


def build_procrastination_input(
    request: CheckUrlRequest,
    normalized: NormalizedUrl,
    learning_result: LearningCheckOutput,
) -> ProcrastinationScoreInput:
    return ProcrastinationScoreInput(
        url=normalized.raw_url,
        platform=normalized.platform,
        contentType=normalized.content_type,
        pageTitle=request.page_title,
        timeOfDay=request.time_of_day or MOCK_USER_CONTEXT["timeOfDay"],
        recentTabSequence=request.recent_tab_sequence
        or MOCK_USER_CONTEXT["recentTabSequence"],
        sessionDurationMinutes=request.session_duration_minutes
        or MOCK_USER_CONTEXT["sessionDurationMinutes"],
        learningCheckResult=learning_result,
    )


def map_score_to_action(score: int, confidence: float) -> dict[str, bool | CheckUrlAction]:
    if score <= 40:
        return {"allowed": True, "action": "allow"}

    if score <= 80:
        return {"allowed": True, "action": "soft_alert"}

    if score >= 81 and confidence >= 0.85:
        return {"allowed": False, "action": "hard_block"}

    return {"allowed": True, "action": "soft_alert"}
