import asyncio
from pathlib import Path
import shutil
from fastapi import APIRouter, Depends, HTTPException
from app.config import settings
from app.dependencies import get_api_key
from app.services.gemini_client import get_client
from app.services.job_store import claim_deletion, delete_job, get_job, update_job

router = APIRouter()


def _deletion_paths(job):
    root = Path(settings.upload_dir).resolve()
    asset_dir = (root / job.job_id).resolve()
    # Check the final resolved target before recursive deletion. In particular,
    # reject traversal and junctions/symlinks that target another directory.
    if asset_dir == root or asset_dir.parent != root or asset_dir.name != job.job_id:
        raise ValueError('Asset media directory is outside its expected workspace location')
    original = Path(job.local_path).resolve() if job.local_path else None
    if original and (original == root or not original.is_relative_to(root)):
        raise ValueError('Original media is outside the upload workspace')
    return original, asset_dir


@router.delete('/api/files/{job_id}')
async def delete_video(job_id: str, api_key: str | None = Depends(get_api_key)):
    job = get_job(job_id)
    if not job:
        raise HTTPException(404, 'Job not found')
    if not claim_deletion(job_id):
        raise HTTPException(409, 'Asset is busy. Cancel active analysis or wait for deletion to finish')
    try:
        original, asset_dir = _deletion_paths(job)
    except ValueError as exc:
        update_job(job_id, status='error', error=str(exc), progress='Deletion could not safely continue')
        raise HTTPException(409, str(exc))
    remote_deleted = not bool(job.file_id)
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
        # until its files and record are gone, so analysis cannot start midway.
        try:
            original, asset_dir = _deletion_paths(job)
            if original and original.is_file():
                original.unlink()
            if asset_dir.is_dir():
                shutil.rmtree(asset_dir)
            delete_job(job_id)
        except OSError:
            update_job(job_id, status='error', error='Local media cleanup failed. Close programs using the media and retry deletion.',
                       progress='Deletion incomplete; retry deletion')
            raise HTTPException(500, 'Local media cleanup failed; the asset record was retained so deletion can be retried')
        except ValueError as exc:
            update_job(job_id, status='error', error=str(exc), progress='Deletion could not safely continue')
            raise HTTPException(409, str(exc))
    return {'status': 'deleted', 'remote_deleted': remote_deleted,
            'note': None if remote_deleted else 'Remote provider cleanup could not be confirmed; Google files normally expire after 48 hours.'}
