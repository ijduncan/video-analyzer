from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.dependencies import get_api_key
from app.services.comparison import run_comparison
from app.services.job_store import get_job

router = APIRouter()


class CompareRequest(BaseModel):
    job_id_a: str
    job_id_b: str


@router.post("/api/compare")
async def compare(body: CompareRequest, api_key: str | None = Depends(get_api_key)):
    job_a = get_job(body.job_id_a)
    job_b = get_job(body.job_id_b)

    if not job_a:
        raise HTTPException(404, f"Job A not found: {body.job_id_a}")
    if not job_b:
        raise HTTPException(404, f"Job B not found: {body.job_id_b}")

    if job_a.status != "complete":
        raise HTTPException(400, "Job A analysis not complete")
    if job_b.status != "complete":
        raise HTTPException(400, "Job B analysis not complete")

    result = await run_comparison(
        job_a.file_uri, job_a.mime_type, job_a.summary,
        job_b.file_uri, job_b.mime_type, job_b.summary,
        api_key=api_key,
    )

    return {"comparison": result}
