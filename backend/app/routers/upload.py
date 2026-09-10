import os
import re
import uuid
from pathlib import Path
from urllib.parse import urlparse, parse_qs

import aiofiles
from fastapi import APIRouter, HTTPException, UploadFile
from pydantic import BaseModel

from app.config import settings
from app.services.job_store import Job, create_job
from app.services.media_probe import probe_media, create_poster
from app.utils.video_formats import get_mime_type

router = APIRouter()


@router.post('/api/upload')
async def upload(file: UploadFile):
    if not file.filename:
        raise HTTPException(400, 'No filename provided')
    filename = Path(file.filename.replace('\\', '/')).name
    mime_type = get_mime_type(filename)
    if not mime_type:
        raise HTTPException(400, 'Unsupported video format')
    job_id = str(uuid.uuid4())
    local_path = Path(settings.upload_dir) / f'{job_id}{Path(filename).suffix.lower()}'
    local_path.parent.mkdir(parents=True, exist_ok=True)
    size = 0
    try:
        async with aiofiles.open(local_path, 'wb') as output:
            while chunk := await file.read(1024 * 1024):
                size += len(chunk)
                if size > settings.max_file_size_mb * 1024 * 1024:
                    raise HTTPException(413, f'File too large. Max {settings.max_file_size_mb}MB')
                await output.write(chunk)
        if not size:
            raise HTTPException(400, 'Video file is empty')
        try:
            technical = await probe_media(str(local_path))
        except FileNotFoundError:
            raise HTTPException(503, 'Install ffmpeg and ffprobe to import local media')
        except ValueError as exc:
            raise HTTPException(400, str(exc))
        await create_poster(str(local_path), str(Path(settings.upload_dir) / job_id / 'poster.jpg'), technical['duration_seconds'])
        job = create_job(Job(job_id=job_id, file_id='', file_uri='', mime_type=mime_type,
            filename=filename, size_bytes=size, local_path=str(local_path), technical=technical,
            metadata={'title': Path(filename).stem}))
    except BaseException:
        local_path.unlink(missing_ok=True)
        raise
    finally:
        await file.close()
    return {'job_id': job.job_id, 'file_id': '', 'filename': job.filename,
            'size_bytes': size, 'mime_type': mime_type, 'status': job.status}


class UrlUploadRequest(BaseModel):
    url: str


@router.post('/api/upload-url')
async def upload_url(body: UrlUploadRequest):
    parsed = urlparse(body.url.strip())
    if parsed.scheme not in ('http', 'https'):
        raise HTTPException(400, 'Enter a full YouTube URL')
    host = (parsed.hostname or '').lower()
    if host in ('www.youtube.com', 'youtube.com', 'm.youtube.com'):
        video_id = parse_qs(parsed.query).get('v', [''])[0] if parsed.path == '/watch' else parsed.path.removeprefix('/shorts/')
    elif host == 'youtu.be':
        video_id = parsed.path.lstrip('/')
    else:
        raise HTTPException(400, 'Only YouTube video URLs are supported')
    if not re.fullmatch(r'[\w-]{11}', video_id):
        raise HTTPException(400, 'Invalid YouTube video ID')
    url = f'https://www.youtube.com/watch?v={video_id}'
    job = create_job(Job(job_id=str(uuid.uuid4()), file_id='', file_uri=url, mime_type='video/*',
        filename=f'youtube_{video_id}', size_bytes=0, local_path='', youtube_url=url))
    return {'job_id': job.job_id, 'file_id': '', 'filename': job.filename, 'size_bytes': 0,
            'mime_type': job.mime_type, 'status': job.status, 'youtube_url': url, 'youtube_id': video_id}
