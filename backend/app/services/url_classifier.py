from datetime import UTC, datetime
from typing import Any

from app.config.bad_links import BAD_LINK_RULES, BadLinkRule
from app.schemas.ai import (
    LinkClassificationInput,
    LinkClassificationOutput,
    LearningCheckInput,
    LearningCheckOutput,
    ProcrastinationScoreInput,
)
from app.schemas.check_url import (
    CheckUrlClassification,
    CheckUrlRequest,
    CheckUrlResponse,
    NormalizedUrl,
)
from app.services.ai_link_classification import ai_link_classification
from app.services.ai_learning_check import ai_learning_check
from app.services.ai_procrastination_score import ai_procrastination_score
from app.services.gemini_client import GeminiConfigurationError, GeminiGenerationError
from app.services.supabase_browsing import (
    SessionTable,
    SupabaseBrowsingStore,
    append_visit_id,
)
from app.services.supabase_client import AuthenticatedUser
from app.utils.normalize_url import build_debounce_url_key, normalize_url


MAX_POLL_GAP_SECONDS = 30.0
MIN_RETRY_GAP_SECONDS = 0.5
PRODUCTIVE_RECOVERY_SECONDS = 120.0
BAD_CONFIDENCE_THRESHOLD = 0.75

MOCK_USER_CONTEXT = {
    "timeOfDay": "21:30",
    "recentTabSequence": [
        "https://learn.uwaterloo.ca/control-systems-assignment",
        "https://youtube.com/results?search_query=pid+controller",
        "https://youtube.com/shorts/xyz",
    ],
    "sessionDurationMinutes": 12,
}


async def classify_url(
    request: CheckUrlRequest,
    *,
    user: AuthenticatedUser,
    store: SupabaseBrowsingStore,
    now: datetime | None = None,
) -> CheckUrlResponse:
    now = now or datetime.now(UTC)
    normalized = normalize_url(request.url)
    visit, elapsed_seconds = await get_or_create_current_visit(
        request=request,
        normalized=normalized,
        user=user,
        store=store,
        now=now,
    )

    bad_domains = await store.list_bad_domains(user)
    bad_domain = find_bad_domain_match(
        normalized=normalized,
        bad_domains=bad_domains,
    )

    if bad_domain is None:
        return await handle_good_link_flow(
            user=user,
            store=store,
            visit=visit,
            elapsed_seconds=elapsed_seconds,
            now=now,
            classification="good",
            reason=None,
            confidence=None,
        )

    try:
        learning_result = await call_gemini_learning_analyzer(request, normalized)
    except (GeminiConfigurationError, GeminiGenerationError):
        learning_result = None

    if learning_result and learning_result.is_learning:
        return await handle_good_link_flow(
            user=user,
            store=store,
            visit=visit,
            elapsed_seconds=elapsed_seconds,
            now=now,
            classification="learning",
            reason=learning_result.reason,
            confidence=learning_result.confidence,
        )

    try:
        classification_result = await call_gemini_classification_analyzer(
            request,
            normalized,
        )
    except (GeminiConfigurationError, GeminiGenerationError):
        await end_active_session(user, store, "allowed_sessions")
        return await handle_unsure_link_flow(
            user=user,
            store=store,
            visit=visit,
            elapsed_seconds=elapsed_seconds,
            reason="Gemini classification unavailable.",
            confidence=None,
            classification="unsure",
        )

    if classification_result.classification == "okay":
        return await handle_good_link_flow(
            user=user,
            store=store,
            visit=visit,
            elapsed_seconds=elapsed_seconds,
            now=now,
            classification="okay",
            reason=classification_result.reason,
            confidence=classification_result.confidence,
        )

    await end_active_session(user, store, "allowed_sessions")

    if classification_result.classification == "unsure":
        return await handle_unsure_link_flow(
            user=user,
            store=store,
            visit=visit,
            elapsed_seconds=elapsed_seconds,
            reason=classification_result.reason,
            confidence=classification_result.confidence,
            classification="unsure",
        )

    if classification_result.confidence < BAD_CONFIDENCE_THRESHOLD:
        return await handle_unsure_link_flow(
            user=user,
            store=store,
            visit=visit,
            elapsed_seconds=elapsed_seconds,
            reason=classification_result.reason,
            confidence=classification_result.confidence,
            classification="bad",
        )

    return await handle_bad_link_flow(
        user=user,
        store=store,
        visit=visit,
        elapsed_seconds=elapsed_seconds,
        now=now,
        reason=classification_result.reason,
        confidence=classification_result.confidence,
    )


async def get_or_create_current_visit(
    *,
    request: CheckUrlRequest,
    normalized: NormalizedUrl,
    user: AuthenticatedUser,
    store: SupabaseBrowsingStore,
    now: datetime,
) -> tuple[dict[str, Any], float]:
    normalized_url = build_debounce_url_key(normalized)
    latest_visit = await store.get_latest_visit(user)

    if latest_visit and latest_visit.get("normalized_url") == normalized_url:
        elapsed_seconds = _elapsed_since(
            latest_visit.get("last_seen_at") or latest_visit.get("timestamp"),
            now,
        )
        duration = float(latest_visit.get("duration") or 0) + elapsed_seconds
        visit = await store.update_visit(
            user,
            latest_visit,
            duration=duration,
            page_title=request.page_title,
            now=now,
        )
        return visit, elapsed_seconds

    visit = await store.create_visit(
        user,
        url=request.url,
        normalized_url=normalized_url,
        domain=normalized.hostname,
        page_title=request.page_title,
        now=now,
    )
    return visit, 0.0


async def handle_good_link_flow(
    *,
    user: AuthenticatedUser,
    store: SupabaseBrowsingStore,
    visit: dict[str, Any],
    elapsed_seconds: float,
    now: datetime,
    classification: CheckUrlClassification,
    reason: str | None,
    confidence: float | None,
) -> CheckUrlResponse:
    allowed_session = await start_or_extend_session(
        user,
        store,
        "allowed_sessions",
        visit,
        elapsed_seconds,
        now,
    )
    procrastination_session = await store.get_active_session(
        user,
        "procrastination_session",
    )

    if procrastination_session:
        if float(allowed_session.get("duration") or 0) > PRODUCTIVE_RECOVERY_SECONDS:
            await end_active_session(
                user,
                store,
                "procrastination_session",
                procrastination_session,
            )
            await start_or_extend_session(
                user,
                store,
                "productive_session",
                visit,
                0.0,
                now,
            )
            return CheckUrlResponse(
                allowed=True,
                action="procrastination_ended",
                sessionType="productive",
                reason=(
                    reason
                    or "Productive browsing has continued for over 2 minutes."
                ),
                classification=classification,
                confidence=confidence,
            )

        return CheckUrlResponse(
            allowed=True,
            action="continue",
            sessionType="allowed",
            reason=reason,
            classification=classification,
            confidence=confidence,
        )

    productive_session = await store.get_active_session(user, "productive_session")
    if productive_session is None:
        await start_session(user, store, "productive_session", visit, now)
        return CheckUrlResponse(
            allowed=True,
            action="productive_started",
            sessionType="productive",
            reason=reason,
            classification=classification,
            confidence=confidence,
        )

    await extend_active_session(
        user,
        store,
        "productive_session",
        productive_session,
        visit,
        elapsed_seconds,
    )
    return CheckUrlResponse(
        allowed=True,
        action="continue",
        sessionType="productive",
        reason=reason,
        classification=classification,
        confidence=confidence,
    )


async def handle_unsure_link_flow(
    *,
    user: AuthenticatedUser,
    store: SupabaseBrowsingStore,
    visit: dict[str, Any],
    elapsed_seconds: float,
    reason: str | None,
    confidence: float | None,
    classification: CheckUrlClassification,
) -> CheckUrlResponse:
    procrastination_session = await store.get_active_session(
        user,
        "procrastination_session",
    )
    if procrastination_session:
        await extend_active_session(
            user,
            store,
            "procrastination_session",
            procrastination_session,
            visit,
            elapsed_seconds,
        )
        return CheckUrlResponse(
            allowed=True,
            action="continue",
            sessionType="procrastination",
            reason=reason,
            classification=classification,
            confidence=confidence,
        )

    return CheckUrlResponse(
        allowed=True,
        action="ask_user",
        sessionType=None,
        reason=reason,
        classification=classification,
        confidence=confidence,
    )


async def handle_bad_link_flow(
    *,
    user: AuthenticatedUser,
    store: SupabaseBrowsingStore,
    visit: dict[str, Any],
    elapsed_seconds: float,
    now: datetime,
    reason: str | None,
    confidence: float | None,
) -> CheckUrlResponse:
    procrastination_session = await store.get_active_session(
        user,
        "procrastination_session",
    )
    if procrastination_session:
        await extend_active_session(
            user,
            store,
            "procrastination_session",
            procrastination_session,
            visit,
            elapsed_seconds,
        )
        return CheckUrlResponse(
            allowed=False,
            action="continue",
            sessionType="procrastination",
            reason=reason,
            classification="bad",
            confidence=confidence,
        )

    await end_active_session(user, store, "productive_session")
    await start_session(user, store, "procrastination_session", visit, now)
    return CheckUrlResponse(
        allowed=False,
        action="hard_ban",
        sessionType="procrastination",
        reason=reason,
        classification="bad",
        confidence=confidence,
    )


async def start_or_extend_session(
    user: AuthenticatedUser,
    store: SupabaseBrowsingStore,
    table: SessionTable,
    visit: dict[str, Any],
    elapsed_seconds: float,
    now: datetime,
) -> dict[str, Any]:
    session = await store.get_active_session(user, table)
    if session is None:
        return await start_session(user, store, table, visit, now)

    return await extend_active_session(
        user,
        store,
        table,
        session,
        visit,
        elapsed_seconds,
    )


async def start_session(
    user: AuthenticatedUser,
    store: SupabaseBrowsingStore,
    table: SessionTable,
    visit: dict[str, Any],
    now: datetime,
) -> dict[str, Any]:
    return await store.create_session(
        user,
        table,
        visit_id=visit["id"],
        now=now,
    )


async def extend_active_session(
    user: AuthenticatedUser,
    store: SupabaseBrowsingStore,
    table: SessionTable,
    session: dict[str, Any],
    visit: dict[str, Any],
    elapsed_seconds: float,
) -> dict[str, Any]:
    visits = append_visit_id(session, visit["id"])
    duration = float(session.get("duration") or 0) + elapsed_seconds

    if visits == list(session.get("visits") or []) and elapsed_seconds == 0:
        return session

    return await store.update_session(
        user,
        table,
        session,
        {
            "duration": duration,
            "visits": visits,
        },
    )


async def end_active_session(
    user: AuthenticatedUser,
    store: SupabaseBrowsingStore,
    table: SessionTable,
    session: dict[str, Any] | None = None,
) -> None:
    session = session or await store.get_active_session(user, table)
    if session is None:
        return

    await store.update_session(user, table, session, {"active": False})


async def call_gemini_learning_analyzer(
    request: CheckUrlRequest,
    normalized: NormalizedUrl,
) -> LearningCheckOutput:
    return await ai_learning_check(build_learning_input(request, normalized))


async def call_gemini_classification_analyzer(
    request: CheckUrlRequest,
    normalized: NormalizedUrl,
) -> LinkClassificationOutput:
    return await ai_link_classification(
        build_classification_input(request, normalized),
    )


def find_bad_domain_match(
    *,
    normalized: NormalizedUrl,
    bad_domains: list[str],
) -> str | None:
    for bad_domain in bad_domains:
        normalized_bad_domain = normalize_bad_domain_entry(bad_domain)
        if normalized_bad_domain is None:
            continue

        hostname, pathname = normalized_bad_domain
        host_matches = (
            normalized.hostname == hostname
            or normalized.hostname.endswith(f".{hostname}")
        )
        if not host_matches:
            continue

        if pathname == "/" or normalized.pathname.lower().startswith(pathname):
            return bad_domain

    return None


def normalize_bad_domain_entry(value: str) -> tuple[str, str] | None:
    cleaned = value.strip()
    if not cleaned:
        return None

    url = cleaned if "://" in cleaned else f"https://{cleaned}"
    normalized = normalize_url(url)
    if not normalized.hostname:
        return None

    return normalized.hostname, normalized.pathname.lower()


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


def build_classification_input(
    request: CheckUrlRequest,
    normalized: NormalizedUrl,
) -> LinkClassificationInput:
    return LinkClassificationInput(
        url=normalized.raw_url,
        platform=normalized.platform,
        contentType=normalized.content_type,
        pageTitle=request.page_title,
        timeOfDay=request.time_of_day or MOCK_USER_CONTEXT["timeOfDay"],
        recentTabSequence=request.recent_tab_sequence
        or MOCK_USER_CONTEXT["recentTabSequence"],
        sessionDurationMinutes=request.session_duration_minutes
        or MOCK_USER_CONTEXT["sessionDurationMinutes"],
    )


def _elapsed_since(value: Any, now: datetime) -> float:
    previous = _parse_datetime(value)
    if previous is None:
        return 0.0

    elapsed = (now.astimezone(UTC) - previous).total_seconds()
    if elapsed < MIN_RETRY_GAP_SECONDS:
        return 0.0

    return min(elapsed, MAX_POLL_GAP_SECONDS)


def _parse_datetime(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str):
        normalized_value = value.replace("Z", "+00:00")
        try:
            parsed = datetime.fromisoformat(normalized_value)
        except ValueError:
            return None
    else:
        return None

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)

    return parsed.astimezone(UTC)


def map_score_to_action(score: int, confidence: float) -> dict[str, bool | str]:
    if score <= 40:
        return {"allowed": True, "action": "allow"}

    if score <= 80:
        return {"allowed": True, "action": "soft_alert"}

    if score >= 81 and confidence >= 0.85:
        return {"allowed": False, "action": "hard_block"}

    return {"allowed": True, "action": "soft_alert"}
