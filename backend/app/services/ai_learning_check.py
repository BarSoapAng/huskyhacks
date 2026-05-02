import json

from app.schemas.ai import LearningCheckInput, LearningCheckOutput
from app.services.gemini_client import generate_structured_content


LEARNING_CHECK_SYSTEM_PROMPT = """
You are evaluating whether the current URL content is genuinely productive or educational.

Prioritize avoiding false negatives for educational content. If the page plausibly helps
with studying, work, research, reference lookup, troubleshooting, or practical skill
development, classify it as learning.

Consider:
- Is it educational, instructional, reference, documentation, or work-related content?
- Is the user on a bounded content page, like a specific video, article, post, or lesson?
- Is it a high-risk feed format, like Shorts, Reels, TikTok, Explore, or infinite scroll?
- Could the platform be distracting but the specific content still useful?

Return structured JSON only.
""".strip()


async def ai_learning_check(input_data: LearningCheckInput) -> LearningCheckOutput:
    return await generate_structured_content(
        system_instruction=LEARNING_CHECK_SYSTEM_PROMPT,
        user_prompt=json.dumps(
            input_data.model_dump(by_alias=True),
            ensure_ascii=True,
            indent=2,
        ),
        response_schema=LearningCheckOutput,
        temperature=0.1,
    )
