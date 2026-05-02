import json

from app.schemas.ai import LinkClassificationInput, LinkClassificationOutput
from app.services.gemini_client import generate_structured_content


LINK_CLASSIFICATION_SYSTEM_PROMPT = """
You are classifying whether the current URL should be allowed during a focus session.

Return structured JSON only.

Use exactly one classification:
- okay: the page is probably acceptable, productive, or a reasonable break
- unsure: evidence is mixed or confidence is too low to decide
- bad: the page is very likely procrastination and blocking is justified

Be conservative. Do not classify as bad unless the evidence is strong.
""".strip()


async def ai_link_classification(
    input_data: LinkClassificationInput,
) -> LinkClassificationOutput:
    return await generate_structured_content(
        system_instruction=LINK_CLASSIFICATION_SYSTEM_PROMPT,
        user_prompt=json.dumps(
            input_data.model_dump(by_alias=True),
            ensure_ascii=True,
            indent=2,
        ),
        response_schema=LinkClassificationOutput,
        temperature=0.1,
    )
