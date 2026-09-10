from fastapi import APIRouter, HTTPException, Query, Depends
from sse_starlette.sse import EventSourceResponse
from app.dependencies import get_api_key
from app.config import settings
from app.services.analyzer import run_analysis
from app.services.file_manager import ensure_remote_file
from app.services.job_store import get_job, claim_analysis, update_job
import asyncio
import json
from datetime import datetime, timezone

router = APIRouter()


@router.get('/api/analyze/{job_id}')
async def analyze(job_id: str, fps: float = Query(default=1, ge=0.5, le=5),
    mode: str = Query(default='flash_pro', pattern='^(flash_only|flash_pro)$'),
    custom_prompt: str = Query(default='', max_length=10000),
    api_key: str | None = Depends(get_api_key)):
    job = get_job(job_id)
    if not job:
        raise HTTPException(404, 'Job not found')
    if not (api_key or settings.google_api_key):
        raise HTTPException(400, 'Configure a Gemini key in Settings or .env')
    if not claim_analysis(job_id):
        raise HTTPException(409, 'Job is already analyzing')

    async def events():
        try:
            await ensure_remote_file(job, api_key)
            async for event in run_analysis(job, fps, mode, custom_prompt=custom_prompt.strip() or None, api_key=api_key):
                yield event
        except asyncio.CancelledError:
            latest = get_job(job_id)
            update_job(job_id, status='error', error='Connection closed. Completed sections preserved.', progress='Interrupted',
                       analysis_progress={**(latest.analysis_progress if latest else {}), 'stage': 'interrupted',
                                          'updated_at': datetime.now(timezone.utc).isoformat()})
            raise
        except Exception as exc:
            message = f'Analysis failed ({type(exc).__name__}). Check provider access and retry.'
            update_job(job_id, status='error', error=message)
            yield {'event': 'error_event', 'data': json.dumps({'message': message, 'recoverable': False})}
    return EventSourceResponse(events())
