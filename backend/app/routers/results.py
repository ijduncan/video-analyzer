from fastapi import APIRouter, HTTPException

from app.services.job_store import get_job

router = APIRouter()


@router.get("/api/results/{job_id}")
async def get_results(job_id: str):
    job = get_job(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    if job.status != "complete":
        raise HTTPException(400, f"Analysis not complete. Current status: {job.status}")

    return {
        "job_id": job.job_id,
        "flash": job.flash_result,
        "deep": job.deep_results,
        "summary": job.summary,
        "cost_estimate": job.cost_estimate,
    }
