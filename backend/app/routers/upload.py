import os
import re
import uuid
from pathlib import Path

import aiofiles
from fastapi import APIRouter, Depends, HTTPException, UploadFile
from pydantic import BaseModel

from app.config import settings
from app.dependencies import get_api_key
from app.services.file_manager import poll_until_active, upload_video
from app.services.job_store import Job, create_job
from app.utils.video_formats import get_mime_type

router = APIRouter()


@router.post("/api/upload")
async def upload(file: UploadFile, api_key: str | None = Depends(get_api_key)):
    if not file.filename:
        raise HTTPException(400, "No filename provided")

    mime_type = get_mime_type(file.filename)
    if not mime_type:
        raise HTTPException(
            400,
            f"Unsupported file format. Allowed: mp4, mov, avi, mpeg, flv, mpg, webm, wmv, 3gpp",
        )

    # Save to disk
    job_id = str(uuid.uuid4())
    ext = Path(file.filename).suffix
    local_path = os.path.join(settings.upload_dir, f"{job_id}{ext}")
    os.makedirs(settings.upload_dir, exist_ok=True)

    size = 0
    async with aiofiles.open(local_path, "wb") as f:
        while chunk := await file.read(1024 * 1024):  # 1MB chunks
            size += len(chunk)
            if size > settings.max_file_size_mb * 1024 * 1024:
                os.remove(local_path)
                raise HTTPException(413, f"File too large. Max {settings.max_file_size_mb}MB")
            await f.write(chunk)

    # Upload to Google File API
    try:
        uploaded = await upload_video(local_path, mime_type, api_key=api_key)
        file_obj = await poll_until_active(uploaded.name, api_key=api_key)
    except Exception as e:
        os.remove(local_path)
        raise HTTPException(500, f"Failed to process video: {str(e)}")

    job = create_job(
        Job(
            job_id=job_id,
            file_id=file_obj.name,
            file_uri=file_obj.uri,
            mime_type=mime_type,
            filename=file.filename,
            size_bytes=size,
            local_path=local_path,
        )
    )

    return {
        "job_id": job.job_id,
        "file_id": job.file_id,
        "filename": job.filename,
        "size_bytes": job.size_bytes,
        "mime_type": job.mime_type,
        "status": job.status,
    }


_YT_PATTERN = re.compile(
    r"(?:https?://)?(?:www\.)?(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/shorts/)([\w-]{11})"
)


class UrlUploadRequest(BaseModel):
    url: str


@router.post("/api/upload-url")
async def upload_url(body: UrlUploadRequest):
    url = body.url.strip()
    match = _YT_PATTERN.search(url)
    if not match:
        raise HTTPException(400, "Invalid YouTube URL")

    video_id = match.group(1)
    job_id = str(uuid.uuid4())

    # Gemini accepts YouTube URLs directly via Part.from_uri
    job = create_job(
        Job(
            job_id=job_id,
            file_id="",
            file_uri=url,
            mime_type="video/*",
            filename=f"youtube_{video_id}",
            size_bytes=0,
            local_path="",
            youtube_url=url,
        )
    )

    return {
        "job_id": job.job_id,
        "file_id": "",
        "filename": job.filename,
        "size_bytes": 0,
        "mime_type": "video/*",
        "status": job.status,
        "youtube_url": url,
        "youtube_id": video_id,
    }
