import os

from fastapi import APIRouter, HTTPException

from app.services.file_manager import delete_file
from app.services.job_store import delete_job, get_job

router = APIRouter()


@router.delete("/api/files/{job_id}")
async def delete_video(job_id: str):
    job = get_job(job_id)
    if not job:
        raise HTTPException(404, "Job not found")

    try:
        await delete_file(job.file_id)
    except Exception:
        pass  # File may already be expired

    if os.path.exists(job.local_path):
        os.remove(job.local_path)

    delete_job(job_id)
    return {"status": "deleted"}
