"""Read source facts from ffprobe, never infer them with a language model."""
import asyncio
import json
from fractions import Fraction
from pathlib import Path


async def _stop_process(proc):
    """Release source-file handles before upload cancellation can remove a file."""
    if proc.returncode is None:
        try:
            proc.kill()
        except ProcessLookupError:
            pass
    await proc.wait()


async def probe_media(path: str) -> dict:
    proc = await asyncio.create_subprocess_exec(
        "ffprobe", "-v", "error", "-show_format", "-show_streams", "-of", "json", path,
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=60)
    except asyncio.TimeoutError:
        await _stop_process(proc)
        raise ValueError("Media inspection timed out")
    except asyncio.CancelledError:
        await _stop_process(proc)
        raise
    if proc.returncode:
        raise ValueError("This file could not be read as video")
    data = json.loads(stdout)
    streams = data.get("streams", [])
    video = next((s for s in streams if s.get("codec_type") == "video"), None)
    if video is None:
        raise ValueError("No video stream found in this file")
    fmt = data.get("format", {})
    rate = video.get("avg_frame_rate", "0/1")
    try:
        fps = float(Fraction(rate))
    except (ValueError, ZeroDivisionError):
        fps = 0
    return {
        "duration_seconds": float(fmt.get("duration", video.get("duration", 0))),
        "width": video.get("width", 0), "height": video.get("height", 0),
        "frame_rate": fps, "frame_rate_fraction": rate, "codec": video.get("codec_name", ""),
        "source_timecode": video.get("tags", {}).get("timecode") or fmt.get("tags", {}).get("timecode") or
            next((s.get("tags", {}).get("timecode") for s in streams if s.get("tags", {}).get("timecode")), None),
        "has_audio": any(s.get("codec_type") == "audio" for s in streams),
        "pixel_format": video.get("pix_fmt"), "color_space": video.get("color_space"),
        "rotation": next((s.get("rotation") for s in video.get("side_data_list", []) if "rotation" in s), 0),
    }


async def create_poster(path: str, output: str, duration: float):
    Path(output).parent.mkdir(parents=True, exist_ok=True)
    proc = await asyncio.create_subprocess_exec(
        "ffmpeg", "-v", "error", "-ss", str(min(1, max(0, duration / 3))), "-i", path,
        "-frames:v", "1", "-vf", "scale=640:-2", "-q:v", "3", "-y", output,
        stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL,
    )
    try:
        await asyncio.wait_for(proc.wait(), timeout=45)
    except asyncio.TimeoutError:
        await _stop_process(proc)
    except asyncio.CancelledError:
        await _stop_process(proc)
        raise
