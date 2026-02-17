import asyncio
import logging

from google.genai import types

from app.models.analysis import (
    FlashAnalysis,
    Scene,
    SceneDetectionResult,
    Shot,
    ShotDetectionResult,
)
from app.prompts.scene_prompt import SCENE_DETECTION_PROMPT
from app.prompts.shot_prompt import SHOT_DETECTION_PROMPT
from app.services.gemini_client import get_client

logger = logging.getLogger(__name__)


def time_to_seconds(t: str) -> float:
    """Convert MM:SS or HH:MM:SS to seconds."""
    parts = t.strip().split(":")
    try:
        if len(parts) == 2:
            return int(parts[0]) * 60 + float(parts[1])
        if len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
    except (ValueError, IndexError):
        pass
    return 0.0


async def run_scene_detection(
    file_uri: str,
    mime_type: str,
    api_key: str | None = None,
) -> tuple[SceneDetectionResult, dict]:
    """Stage 1: detect structural scene boundaries across the full video.

    Uses the full video at Gemini's default sampling rate — 1 fps is fine
    for finding major structural breaks.

    Returns (SceneDetectionResult, usage_dict).
    """
    client = get_client(api_key)
    video_part = types.Part.from_uri(file_uri=file_uri, mime_type=mime_type)

    response = await asyncio.to_thread(
        client.models.generate_content,
        model="gemini-2.5-flash",
        contents=[video_part, SCENE_DETECTION_PROMPT],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=SceneDetectionResult,
        ),
    )

    usage = {}
    if response.usage_metadata:
        usage = {
            "input_tokens": response.usage_metadata.prompt_token_count or 0,
            "output_tokens": response.usage_metadata.candidates_token_count or 0,
        }

    result = SceneDetectionResult.model_validate_json(response.text)
    logger.info(f"Stage 1 complete: {result.total_scenes} scenes detected")
    return result, usage


async def run_shot_detection(
    file_uri: str,
    mime_type: str,
    scene_outline: "SceneDetectionResult.scenes[0]",
    shot_number_offset: int,
    fps: float,
    api_key: str | None = None,
) -> tuple[list[Shot], dict]:
    """Stage 2: detect every shot within a single scene at high fps.

    Uses VideoMetadata to clip the video to just this scene and sample at
    the requested fps for accurate cut detection.

    Returns (shots_list, usage_dict).
    """
    client = get_client(api_key)

    start_secs = time_to_seconds(scene_outline.start_time)
    end_secs = time_to_seconds(scene_outline.end_time)

    prompt = SHOT_DETECTION_PROMPT.format(
        scene_number=scene_outline.scene_number,
        scene_title=scene_outline.scene_title,
        start_time=scene_outline.start_time,
        end_time=scene_outline.end_time,
        shot_number_offset=shot_number_offset,
    )

    video_part = types.Part(
        file_data=types.FileData(file_uri=file_uri, mime_type=mime_type),
        video_metadata=types.VideoMetadata(
            start_offset=f"{int(start_secs)}s",
            end_offset=f"{int(end_secs)}s",
            fps=fps,
        ),
    )

    response = await asyncio.to_thread(
        client.models.generate_content,
        model="gemini-2.5-flash",
        contents=[video_part, prompt],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=ShotDetectionResult,
        ),
    )

    usage = {}
    if response.usage_metadata:
        usage = {
            "input_tokens": response.usage_metadata.prompt_token_count or 0,
            "output_tokens": response.usage_metadata.candidates_token_count or 0,
        }

    result = ShotDetectionResult.model_validate_json(response.text)

    # Re-number shots sequentially using the global offset
    for i, shot in enumerate(result.shots):
        shot.shot_number = shot_number_offset + i

    logger.info(
        f"Stage 2 complete: scene {scene_outline.scene_number} → {len(result.shots)} shots"
    )
    return result.shots, usage


async def run_flash_pass(
    file_uri: str,
    mime_type: str,
    fps: float = 4.0,
    api_key: str | None = None,
) -> tuple[FlashAnalysis, dict]:
    """Convenience wrapper that runs both stages without progress events.

    Prefer calling run_scene_detection / run_shot_detection directly from
    analyzer.py when you need to yield SSE progress events between stages.
    """
    total_input = 0
    total_output = 0

    scenes_result, s1_usage = await run_scene_detection(file_uri, mime_type, api_key)
    total_input += s1_usage.get("input_tokens", 0)
    total_output += s1_usage.get("output_tokens", 0)

    scenes: list[Scene] = []
    shot_counter = 1

    for outline in scenes_result.scenes:
        try:
            shots, s2_usage = await run_shot_detection(
                file_uri, mime_type, outline, shot_counter, fps, api_key
            )
            total_input += s2_usage.get("input_tokens", 0)
            total_output += s2_usage.get("output_tokens", 0)
        except Exception as e:
            logger.error(f"Shot detection failed for scene {outline.scene_number}: {e}")
            shots = []

        scenes.append(Scene(
            scene_number=outline.scene_number,
            scene_title=outline.scene_title,
            scene_description=outline.scene_description,
            start_time=outline.start_time,
            end_time=outline.end_time,
            shots=shots,
        ))
        shot_counter += len(shots)

    flash_analysis = FlashAnalysis(
        total_duration=scenes_result.total_duration,
        total_scenes=len(scenes),
        total_shots=shot_counter - 1,
        scenes=scenes,
    )
    combined_usage = {"input_tokens": total_input, "output_tokens": total_output}
    logger.info(
        f"Flash pass complete: {flash_analysis.total_scenes} scenes, "
        f"{flash_analysis.total_shots} shots"
    )
    return flash_analysis, combined_usage
