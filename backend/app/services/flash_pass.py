import asyncio
import logging
import time

from google.genai import types

from app.config import settings
from app.models.analysis import (
    FlashAnalysis,
    Scene,
    SceneDetectionResult,
    SceneOutline,
    Shot,
    ShotDetectionResult,
)
from app.prompts.scene_prompt import SCENE_DETECTION_PROMPT
from app.prompts.shot_prompt import SHOT_DETECTION_PROMPT
from app.services.gemini_client import get_client
from app.services.analysis_support import (
    EVIDENCE_INSTRUCTION, clip_offset, extract_usage, response_text,
    time_to_seconds, validate_scenes, validate_shots,
)

logger = logging.getLogger(__name__)
REQUEST_TIMEOUT_SECONDS = 90


async def _generate(client, *, stage: str, schema, contents):
    """Bound transport and await time; use an async request for cancellation."""
    started = time.monotonic()
    config = {
        "system_instruction": EVIDENCE_INSTRUCTION,
        "response_mime_type": "application/json", "response_schema": schema,
        "max_output_tokens": 16384,
        "http_options": types.HttpOptions(
            timeout=int(REQUEST_TIMEOUT_SECONDS * 1000),
            retry_options=types.HttpRetryOptions(attempts=1),
        ),
    }
    if settings.gemini_analysis_model.startswith("gemini-3."):
        config["thinking_config"] = types.ThinkingConfig(thinking_level="LOW")
    try:
        return await asyncio.wait_for(client.aio.models.generate_content(
            model=settings.gemini_analysis_model, contents=contents,
            config=types.GenerateContentConfig(**config),
        ), timeout=REQUEST_TIMEOUT_SECONDS)
    finally:
        logger.info("%s request finished after %.1fs", stage, time.monotonic() - started)


async def run_scene_detection(
    file_uri: str,
    mime_type: str,
    api_key: str | None = None,
    duration_seconds: float | None = None,
) -> tuple[SceneDetectionResult, dict]:
    """Stage 1: detect structural scene boundaries across the full video.

    Uses the full video at Gemini's default sampling rate — 1 fps is fine
    for finding major structural breaks.

    Returns (SceneDetectionResult, usage_dict).
    """
    client = get_client(api_key)
    video_part = types.Part.from_uri(file_uri=file_uri, mime_type=mime_type)

    response = await _generate(
        client, stage="scene_detection", schema=SceneDetectionResult,
        contents=[video_part, SCENE_DETECTION_PROMPT + (
            f"\nSource duration measured by the media probe: {duration_seconds:.6f} seconds."
            if duration_seconds else ""
        )],
    )

    usage = extract_usage(response, settings.gemini_analysis_model, "scene_detection")
    result = validate_scenes(
        SceneDetectionResult.model_validate_json(response_text(response)), duration_seconds,
    )
    logger.info(f"Stage 1 complete: {result.total_scenes} scenes detected")
    return result, usage


async def run_shot_detection(
    file_uri: str,
    mime_type: str,
    scene_outline: SceneOutline,
    shot_number_offset: int,
    fps: float,
    api_key: str | None = None,
) -> tuple[list[Shot], dict]:
    """Stage 2: estimate shots and evidence within a bounded scene.

    Uses VideoMetadata to clip the video to just this scene and sample at
    the requested fps. Model boundaries remain approximate.

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
    if scene_outline.scene_title.startswith("Section "):
        prompt += (
            "\nThis interval is a processing section, not an editorial scene. "
            "Do not invent a cut at its start or end. A continuous shot may be "
            "partially visible at either boundary; describe only its visible portion. "
            "Use absolute ORIGINAL-source timestamps within the provided interval."
        )

    video_part = types.Part(
        file_data=types.FileData(file_uri=file_uri, mime_type=mime_type),
        video_metadata=types.VideoMetadata(
            start_offset=clip_offset(start_secs),
            end_offset=clip_offset(end_secs),
            fps=fps,
        ),
    )

    response = await _generate(
        client, stage="shot_analysis", schema=ShotDetectionResult,
        contents=[video_part, prompt],
    )

    usage = extract_usage(response, settings.gemini_analysis_model, "shot_analysis")
    result = ShotDetectionResult.model_validate_json(response_text(response))
    result.shots = validate_shots(result.shots, start_secs, end_secs, shot_number_offset)

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
            logger.warning("Shot detection failed for scene %s (%s)", outline.scene_number, type(e).__name__)
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
        analysis_warnings=scenes_result.analysis_warnings,
        model=settings.gemini_analysis_model,
    )
    if flash_analysis.total_shots == 0:
        raise ValueError("No valid shot metadata was generated")
    combined_usage = {"input_tokens": total_input, "output_tokens": total_output}
    logger.info(
        f"Flash pass complete: {flash_analysis.total_scenes} scenes, "
        f"{flash_analysis.total_shots} shots"
    )
    return flash_analysis, combined_usage
