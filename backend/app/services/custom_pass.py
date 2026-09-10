import asyncio
import json
import logging

from google.genai import types

from app.config import settings
from app.services.gemini_client import get_client
from app.services.analysis_support import EVIDENCE_INSTRUCTION, extract_usage, response_text

logger = logging.getLogger(__name__)


async def run_custom_pass(
    file_uri: str, mime_type: str, prompt: str, api_key: str | None = None,
) -> tuple[dict, dict]:
    """Run Pass 4: Custom user prompt against the full video.

    Returns (freeform_result_dict, usage_metadata_dict).
    """
    client = get_client(api_key)

    video_part = types.Part.from_uri(file_uri=file_uri, mime_type=mime_type)
    text = (
        f"{prompt}\n\n"
        "Respond with a JSON object. Structure your response however is most "
        "appropriate for the question asked. Use descriptive keys."
    )

    response = await asyncio.to_thread(
        client.models.generate_content,
        model=settings.gemini_deep_model,
        contents=[video_part, text],
        config=types.GenerateContentConfig(
            http_options=types.HttpOptions(timeout=120_000, retry_options=types.HttpRetryOptions(attempts=1)),
            system_instruction=EVIDENCE_INSTRUCTION,
            response_mime_type="application/json",
        ),
    )

    usage = extract_usage(response, settings.gemini_deep_model, "custom")
    result = json.loads(response_text(response))
    if not isinstance(result, dict):
        raise ValueError("Custom analysis must return a JSON object")
    logger.info("Custom pass complete")
    return result, usage
