import asyncio
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)


def _time_to_seconds(time_str: str) -> float:
    from app.services.analysis_support import time_to_seconds
    return time_to_seconds(time_str)


async def extract_thumbnails(
    video_path: str, job_id: str, scenes: list[dict], upload_dir: str
) -> str:
    """Extract one thumbnail per shot from the video file.

    Returns the thumbnail directory path.
    """
    thumb_dir = os.path.join(upload_dir, job_id, "thumbs")
    os.makedirs(thumb_dir, exist_ok=True)

    tasks = []
    gate = asyncio.Semaphore(3)
    async def extract_bounded(seconds, output):
        async with gate:
            return await _extract_frame(video_path, seconds, output)
    for scene in scenes:
        for shot in scene.get("shots", []):
            shot_num = shot.get("shot_number", 0)
            start_time = shot.get("start_time", "0:00")
            secs = _time_to_seconds(start_time)
            out_path = os.path.join(thumb_dir, f"shot_{shot_num}.jpg")
            tasks.append(extract_bounded(secs, out_path))

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
            "-vf", "scale=640:-2",
            "-q:v", "3",
            "-y",
            output_path,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        try:
            await asyncio.wait_for(proc.wait(), timeout=45)
        except (asyncio.TimeoutError, asyncio.CancelledError):
            proc.kill()
            await proc.wait()
            raise
        return proc.returncode == 0
    except Exception as e:
        logger.warning(f"Failed to extract frame at {seconds}s: {e}")
        return False
