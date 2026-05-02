import json

from app.schemas.ai import ProcrastinationScoreInput, ProcrastinationScoreOutput
from app.services.gemini_client import generate_structured_content


PROCRASTINATION_SCORE_SYSTEM_PROMPT = """
You are scoring whether the user's current URL likely represents procrastination.

Return structured JSON only.

Score from 0 to 100:
- 0-40: very likely not procrastinating
- 41-80: uncertain
- 81-100: very likely procrastinating and eligible for hard block

Prioritize minimizing false positives. Do not assign a high score unless several
signals align.

Consider:
- Whether the page is educational, instructional, reference, or work-related
- Whether the page is short-form, feed-based, autoplay-based, or recommendation-driven
- Whether the user came from productive pages into distracting content
- Whether the content is entertainment, social browsing, or unrelated
- Whether the user may be taking a reasonable break
- Whether the evidence is strong enough to justify blocking
""".strip()


async def ai_procrastination_score(
    input_data: ProcrastinationScoreInput,
) -> ProcrastinationScoreOutput:
    return await generate_structured_content(
        system_instruction=PROCRASTINATION_SCORE_SYSTEM_PROMPT,
        user_prompt=json.dumps(
            input_data.model_dump(by_alias=True),
            ensure_ascii=True,
            indent=2,
        ),
        response_schema=ProcrastinationScoreOutput,
        temperature=0.1,
    )
