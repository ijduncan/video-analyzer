from fastapi import APIRouter, HTTPException

from app.services.job_store import get_job

router = APIRouter()


@router.get("/api/status/{job_id}")
async def get_status(job_id: str):
    job = get_job(job_id)
    if not job:
        raise HTTPException(404, "Job not found")

    return {
        "job_id": job.job_id,
        "status": job.status,
        "filename": job.filename,
        "current_pass": job.current_pass,
        "current_scene": job.current_scene,
        "total_scenes": job.total_scenes,
        "progress": job.progress,
        "analysis_progress": job.analysis_progress,
        "error": job.error,
    }
