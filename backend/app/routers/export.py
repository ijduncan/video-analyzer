from pathlib import Path
from urllib.parse import quote
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response
from app.services import export_service
from app.services.job_store import get_job

router = APIRouter()


@router.get('/api/export/{job_id}')
async def export_results(job_id: str, format: str = Query(default='json', pattern='^(json|csv|pdf|markdown|edl|fcpxml)$')):
    job = get_job(job_id)
    if not job:
        raise HTTPException(404, 'Job not found')
    if job.status != 'complete':
        raise HTTPException(400, 'Analysis not complete')
    types = {'json': ('application/json', 'json'), 'csv': ('text/csv', 'csv'),
             'pdf': ('application/pdf', 'pdf'), 'markdown': ('text/markdown', 'md'),
             'edl': ('text/plain', 'edl'), 'fcpxml': ('application/xml', 'fcpxml')}
    media_type, extension = types[format]
    try:
        content = getattr(export_service, f'export_{format}')(job)
    except ValueError as exc:
        raise HTTPException(422, str(exc))
    name = quote(f'{Path(job.filename).stem}_analysis.{extension}')
    return Response(content=content, media_type=media_type,
                    headers={'Content-Disposition': f"attachment; filename*=UTF-8''{name}"})
