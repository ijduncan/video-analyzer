import asyncio
import json
import logging

from google.genai import types

from app.services.gemini_client import get_client

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
        model="gemini-2.5-pro",
        contents=[video_part, text],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
        ),
    )

    usage = {}
    if response.usage_metadata:
        usage = {
            "input_tokens": response.usage_metadata.prompt_token_count or 0,
            "output_tokens": response.usage_metadata.candidates_token_count or 0,
        }

    result = json.loads(response.text)
    logger.info("Custom pass complete")
    return result, usage
