import asyncio
import logging

from google.genai import types

from app.models.analysis import FlashAnalysis, VideoSummary
from app.prompts.summary_prompt import SUMMARY_PROMPT
from app.services.gemini_client import get_client

logger = logging.getLogger(__name__)


async def run_summary_pass(
    file_uri: str, mime_type: str, flash_result: FlashAnalysis, api_key: str | None = None,
) -> tuple[VideoSummary, dict]:
    """Run Pass 3: full video summary with Gemini Pro.

    Returns (parsed_result, usage_metadata_dict).
    """
    client = get_client(api_key)

    video_part = types.Part.from_uri(file_uri=file_uri, mime_type=mime_type)

    context = (
        f"This video has {flash_result.total_scenes} scenes and {flash_result.total_shots} shots, "
        f"with a total duration of {flash_result.total_duration}.\n\n{SUMMARY_PROMPT}"
    )

    response = await asyncio.to_thread(
        client.models.generate_content,
        model="gemini-2.5-pro",
        contents=[video_part, context],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=VideoSummary,
        ),
    )

    usage = {}
    if response.usage_metadata:
        usage = {
            "input_tokens": response.usage_metadata.prompt_token_count or 0,
            "output_tokens": response.usage_metadata.candidates_token_count or 0,
        }

    parsed = VideoSummary.model_validate_json(response.text)
    logger.info("Summary pass complete")
    return parsed, usage
