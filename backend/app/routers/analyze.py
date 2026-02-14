from fastapi import APIRouter, HTTPException, Query
from sse_starlette.sse import EventSourceResponse

from app.services.analyzer import run_analysis
from app.services.job_store import get_job

router = APIRouter()


@router.get("/api/analyze/{job_id}")
async def analyze(
    job_id: str,
    fps: float = Query(default=1.0, ge=0.5, le=5.0),
    mode: str = Query(default="flash_pro", pattern="^(flash_only|flash_pro)$"),
    custom_prompt: str = Query(default=""),
    api_key: str = Query(default="", alias="api_key"),
):
    job = get_job(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    if job.status not in ("ready", "complete", "error"):
        raise HTTPException(409, f"Job is currently {job.status}")

    prompt = custom_prompt.strip() or None
    key = api_key.strip() or None

    async def event_generator():
        async for event in run_analysis(job, fps, mode, custom_prompt=prompt, api_key=key):
            yield event

    return EventSourceResponse(event_generator())
