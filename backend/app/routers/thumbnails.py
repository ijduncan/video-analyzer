import os

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.config import settings

router = APIRouter()


@router.get("/api/thumbnails/{job_id}/{shot_number}")
async def get_thumbnail(job_id: str, shot_number: int):
    path = os.path.join(settings.upload_dir, job_id, "thumbs", f"shot_{shot_number}.jpg")
    if not os.path.isfile(path):
        raise HTTPException(404, "Thumbnail not found")
    return FileResponse(path, media_type="image/jpeg")
