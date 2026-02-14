import asyncio
import json
import logging

from google.genai import types

from app.services.gemini_client import get_client

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
        model="gemini-2.5-flash",
        contents=[video_part, prompt],
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
    matches = result.get("matches", [])
    logger.info(f"Shot matching found {len(matches)} pairs")
    return matches, usage
