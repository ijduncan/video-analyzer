import asyncio
import json
import logging
import math

from google.genai import types

from app.config import settings
from app.services.gemini_client import get_client
from app.services.analysis_support import EVIDENCE_INSTRUCTION, extract_usage, response_text

logger = logging.getLogger(__name__)

SHOT_MATCHING_PROMPT = """Analyze all the shots in this video and identify pairs of visually similar shots.

Here is the shot metadata:
{shot_data}

For each pair of similar shots, provide:
- shot_a: the shot number of the first shot
- shot_b: the shot number of the second shot
- similarity: a score from 0.0 to 1.0 indicating visual similarity
- reasons: a list of specific reasons they are similar (e.g., "same camera angle", "matching color palette", "same subject/person", "similar composition")

Only include pairs with similarity >= 0.5. Return the top 20 most similar pairs sorted by similarity descending.

Return as a JSON object with a single key "matches" containing the array of match objects.
"""


async def run_shot_matching(
    file_uri: str, mime_type: str, flash_result: dict, api_key: str | None = None,
) -> tuple[list[dict], dict]:
    """Run shot matching analysis using Gemini Flash.

    Returns (matches_list, usage_metadata_dict).
    """
    client = get_client(api_key)

    # Build shot metadata summary
    shots = []
    for scene in flash_result.get("scenes", []):
        for shot in scene.get("shots", []):
            shots.append({
                "shot_number": shot.get("shot_number"),
                "scene": scene.get("scene_number"),
                "start_time": shot.get("start_time"),
                "end_time": shot.get("end_time"),
                "shot_type": shot.get("shot_type"),
                "camera_movement": shot.get("camera_movement"),
                "subjects": shot.get("subjects", []),
                "dominant_colors": shot.get("dominant_colors", []),
                "mood": shot.get("mood"),
            })

    prompt = SHOT_MATCHING_PROMPT.format(shot_data=json.dumps(shots, indent=2))

    video_part = types.Part.from_uri(file_uri=file_uri, mime_type=mime_type)

    response = await asyncio.to_thread(
        client.models.generate_content,
        model=settings.gemini_analysis_model,
        contents=[video_part, prompt],
        config=types.GenerateContentConfig(
            system_instruction=EVIDENCE_INSTRUCTION,
            response_mime_type="application/json",
        ),
    )

    usage = extract_usage(response, settings.gemini_analysis_model, "shot_matching")
    result = json.loads(response_text(response))
    ids = {shot["shot_number"] for shot in shots}
    matches, seen = [], set()
    for match in result.get("matches", []):
        if not isinstance(match, dict):
            continue
        a, b = match.get("shot_a"), match.get("shot_b")
        score = match.get("similarity")
        if not isinstance(a, int) or not isinstance(b, int) or a not in ids or b not in ids or a == b:
            continue
        if not isinstance(score, (int, float)) or not math.isfinite(score) or not 0.5 <= score <= 1:
            continue
        pair = tuple(sorted((a, b)))
        if pair in seen:
            continue
        seen.add(pair)
        reasons = [str(r) for r in match.get("reasons", []) if isinstance(r, str)]
        matches.append({"shot_a": a, "shot_b": b, "similarity": score, "reasons": reasons,
                        "score_basis": "model_estimate_uncalibrated"})
    matches = sorted(matches, key=lambda item: item["similarity"], reverse=True)[:20]
    logger.info(f"Shot matching found {len(matches)} pairs")
    return matches, usage
