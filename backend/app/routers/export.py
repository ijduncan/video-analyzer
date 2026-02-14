from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response

from app.services.export_service import (
    export_csv,
    export_edl,
    export_fcpxml,
    export_json,
    export_markdown,
    export_pdf,
)
from app.services.job_store import get_job

router = APIRouter()


@router.get("/api/export/{job_id}")
async def export_results(
    job_id: str,
    format: str = Query(default="json", pattern="^(json|csv|pdf|markdown|edl|fcpxml)$"),
):
    job = get_job(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    if job.status != "complete":
        raise HTTPException(400, "Analysis not complete")

    if format == "json":
        return Response(
            content=export_json(job),
            media_type="application/json",
            headers={"Content-Disposition": f'attachment; filename="{job.filename}_analysis.json"'},
        )
    elif format == "csv":
        return Response(
            content=export_csv(job),
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="{job.filename}_shots.csv"'},
        )
    elif format == "pdf":
        return Response(
            content=export_pdf(job),
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{job.filename}_report.pdf"'},
        )
    elif format == "markdown":
        return Response(
            content=export_markdown(job),
            media_type="text/markdown",
            headers={"Content-Disposition": f'attachment; filename="{job.filename}_analysis.md"'},
        )
    elif format == "edl":
        return Response(
            content=export_edl(job),
            media_type="text/plain",
            headers={"Content-Disposition": f'attachment; filename="{job.filename}.edl"'},
        )
    elif format == "fcpxml":
        return Response(
            content=export_fcpxml(job),
            media_type="application/xml",
            headers={"Content-Disposition": f'attachment; filename="{job.filename}.fcpxml"'},
        )
