import asyncio
import json
import logging

from google.genai import types

from app.config import settings
from app.services.gemini_client import get_client
from app.services.analysis_support import EVIDENCE_INSTRUCTION, response_text

logger = logging.getLogger(__name__)

COMPARISON_PROMPT = """You are comparing two videos. Analyze both videos and provide a detailed comparison.

Video A analysis summary: {summary_a}
Video B analysis summary: {summary_b}

Compare the two videos across these dimensions:
1. **Pacing & Editing**: Which is faster/slower paced? How do editing styles differ?
2. **Visual Style**: Compare color palettes, lighting, composition, camera techniques
3. **Audio**: Compare music, sound design, dialogue approaches
4. **Production Value**: Which has higher production value and why?
5. **Narrative Approach**: How do storytelling styles differ?
6. **Overall Verdict**: A concise summary of key differences and similarities

Return as a JSON object with keys: pacing_comparison, visual_comparison, audio_comparison, production_comparison, narrative_comparison, overall_verdict. Each value should be a descriptive string.
"""


async def run_comparison(
    job_a_uri: str, job_a_mime: str, summary_a: dict | None,
    job_b_uri: str, job_b_mime: str, summary_b: dict | None,
    api_key: str | None = None,
) -> dict:
    """Compare two videos using Gemini Pro.

    Returns comparison result dict.
    """
    client = get_client(api_key)

    prompt = COMPARISON_PROMPT.format(
        summary_a=json.dumps(summary_a, indent=2) if summary_a else "Not available",
        summary_b=json.dumps(summary_b, indent=2) if summary_b else "Not available",
    )

    video_a_part = types.Part.from_uri(file_uri=job_a_uri, mime_type=job_a_mime)
    video_b_part = types.Part.from_uri(file_uri=job_b_uri, mime_type=job_b_mime)

    response = await asyncio.to_thread(
        client.models.generate_content,
        model=settings.gemini_deep_model,
        contents=[video_a_part, video_b_part, prompt],
        config=types.GenerateContentConfig(
            system_instruction=EVIDENCE_INSTRUCTION,
            response_mime_type="application/json",
        ),
    )

    result = json.loads(response_text(response))
    if not isinstance(result, dict):
        raise ValueError("Comparison must return a JSON object")
    logger.info("Comparison complete")
    return result
