import asyncio
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)


def _time_to_seconds(time_str: str) -> float:
    parts = time_str.split(":")
    if len(parts) == 2:
        return int(parts[0]) * 60 + int(parts[1])
    if len(parts) == 3:
        return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
    return 0.0


async def extract_thumbnails(
    video_path: str, job_id: str, scenes: list[dict], upload_dir: str
) -> str:
    """Extract one thumbnail per shot from the video file.

    Returns the thumbnail directory path.
    """
    thumb_dir = os.path.join(upload_dir, job_id, "thumbs")
    os.makedirs(thumb_dir, exist_ok=True)

    tasks = []
    for scene in scenes:
        for shot in scene.get("shots", []):
            shot_num = shot.get("shot_number", 0)
            start_time = shot.get("start_time", "0:00")
            secs = _time_to_seconds(start_time)
            out_path = os.path.join(thumb_dir, f"shot_{shot_num}.jpg")
            tasks.append(_extract_frame(video_path, secs, out_path))

    results = await asyncio.gather(*tasks, return_exceptions=True)
    ok = sum(1 for r in results if r is True)
    logger.info(f"Extracted {ok}/{len(tasks)} thumbnails for job {job_id}")
    return thumb_dir


async def _extract_frame(video_path: str, seconds: float, output_path: str) -> bool:
    try:
        proc = await asyncio.create_subprocess_exec(
            "ffmpeg",
            "-ss", str(seconds),
            "-i", video_path,
            "-frames:v", "1",
            "-q:v", "3",
            "-y",
            output_path,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        await proc.wait()
        return proc.returncode == 0
    except Exception as e:
        logger.warning(f"Failed to extract frame at {seconds}s: {e}")
        return False
