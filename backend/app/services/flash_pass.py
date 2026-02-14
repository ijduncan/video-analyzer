import asyncio
import json
import logging

from google.genai import types

from app.models.analysis import FlashAnalysis
from app.prompts.flash_prompt import FLASH_SCENE_DETECTION_PROMPT
from app.services.gemini_client import get_client

logger = logging.getLogger(__name__)


async def run_flash_pass(file_uri: str, mime_type: str, fps: float = 1.0, api_key: str | None = None) -> tuple[FlashAnalysis, dict]:
    """Run Pass 1: Scene detection with Gemini Flash.

    Returns (parsed_result, usage_metadata_dict).
    """
    client = get_client(api_key)

    video_part = types.Part.from_uri(file_uri=file_uri, mime_type=mime_type)

    response = await asyncio.to_thread(
        client.models.generate_content,
        model="gemini-2.5-flash",
        contents=[video_part, FLASH_SCENE_DETECTION_PROMPT],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=FlashAnalysis,
        ),
    )

    usage = {}
    if response.usage_metadata:
        usage = {
            "input_tokens": response.usage_metadata.prompt_token_count or 0,
            "output_tokens": response.usage_metadata.candidates_token_count or 0,
        }

    parsed = FlashAnalysis.model_validate_json(response.text)
    logger.info(f"Flash pass complete: {parsed.total_scenes} scenes, {parsed.total_shots} shots")
    return parsed, usage
