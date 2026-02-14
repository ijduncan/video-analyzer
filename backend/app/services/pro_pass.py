import asyncio
import json
import logging

from google.genai import types

from app.models.analysis import SceneDeepAnalysis, Scene
from app.prompts.pro_prompt import PRO_SCENE_ANALYSIS_PROMPT
from app.services.gemini_client import get_client

logger = logging.getLogger(__name__)


def _parse_time_to_seconds(time_str: str) -> float:
    """Convert MM:SS or HH:MM:SS to seconds."""
    parts = time_str.split(":")
    if len(parts) == 2:
        return int(parts[0]) * 60 + int(parts[1])
    elif len(parts) == 3:
        return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
    return 0.0


async def run_pro_scene(
    file_uri: str, mime_type: str, scene: Scene, api_key: str | None = None,
) -> tuple[SceneDeepAnalysis, dict]:
    """Run Pass 2 for a single scene: deep analysis with Gemini Pro.

    Returns (parsed_result, usage_metadata_dict).
    """
    client = get_client(api_key)

    start_secs = _parse_time_to_seconds(scene.start_time)
    end_secs = _parse_time_to_seconds(scene.end_time)

    # Build content with video clip
    contents = types.Content(
        parts=[
            types.Part(
                file_data=types.FileData(
                    file_uri=file_uri,
                    mime_type=mime_type,
                ),
                video_metadata=types.VideoMetadata(
                    start_offset=f"{int(start_secs)}s",
                    end_offset=f"{int(end_secs)}s",
                ),
            ),
            types.Part(
                text=f"This is scene {scene.scene_number}: \"{scene.scene_title}\" ({scene.start_time} - {scene.end_time}).\n\n{PRO_SCENE_ANALYSIS_PROMPT}"
            ),
        ]
    )

    response = await asyncio.to_thread(
        client.models.generate_content,
        model="gemini-2.5-pro",
        contents=contents,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=SceneDeepAnalysis,
        ),
    )

    usage = {}
    if response.usage_metadata:
        usage = {
            "input_tokens": response.usage_metadata.prompt_token_count or 0,
            "output_tokens": response.usage_metadata.candidates_token_count or 0,
        }

    parsed = SceneDeepAnalysis.model_validate_json(response.text)
    parsed.scene_number = scene.scene_number
    logger.info(f"Pro pass complete for scene {scene.scene_number}")
    return parsed, usage
