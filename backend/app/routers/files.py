import asyncio
from fastapi import APIRouter, Depends, HTTPException
from app.dependencies import get_api_key
from app.services.gemini_client import get_client
from app.services.job_store import claim_deletion, get_job, update_job
from app.services import media_cleanup
from app.services.media_cleanup import deletion_paths as _deletion_paths

router = APIRouter()


@router.delete('/api/files/{job_id}')
async def delete_video(job_id: str, api_key: str | None = Depends(get_api_key)):
    job = get_job(job_id)
    if not job:
        raise HTTPException(404, 'Job not found')
    if not claim_deletion(job_id):
        raise HTTPException(409, 'Asset is busy. Cancel active analysis or wait for deletion to finish')
    try:
        _deletion_paths(job)
    except ValueError as exc:
        update_job(job_id, status='error', error=str(exc), progress='Deletion could not safely continue')
        raise HTTPException(409, str(exc))
    remote_deleted = not bool(job.file_id)
    from app.services.visual_index import stop
    await stop(job_id)
    try:
        if job.file_id:
            try:
                await asyncio.to_thread(get_client(api_key).files.delete, name=job.file_id)
                remote_deleted = True
            except Exception:
                pass
    finally:
        # Once deletion is claimed, finish local cleanup even if the HTTP
        # request disconnects during remote cleanup. The asset stays reserved
        # until cleanup finishes or is durably queued, so analysis cannot restart midway.
        try:
            cleanup_pending = not await asyncio.to_thread(media_cleanup.cleanup, job)
            media_cleanup.remove_record(job, cleanup_pending)
        except ValueError as exc:
            update_job(job_id, status='error', error=str(exc), progress='Deletion could not safely continue')
            raise HTTPException(409, str(exc))
    notes = []
    if cleanup_pending:
        notes.append('Project removed. Some app-owned files could not yet be cleaned up; cleanup will retry automatically. Original source files are untouched.')
    if not remote_deleted:
        notes.append('Remote provider cleanup could not be confirmed; Google files normally expire after 48 hours.')
    return {'status': 'deleted', 'remote_deleted': remote_deleted, 'cleanup_pending': cleanup_pending,
            'note': ' '.join(notes) or None}
