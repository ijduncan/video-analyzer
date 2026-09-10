from pathlib import Path
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse, Response

from app.config import settings
from app.dependencies import get_api_key
from app.models.library import AssetMetadata, ShotAnnotation, AnalyzeRequest
from app.services.job_store import get_job, list_jobs, update_job, claim_analysis
from app.services.job_runner import start_job, cancel_job
from app.services.library_service import asset_view, shot_views, search_score

router = APIRouter(prefix='/api/library')


def require_job(job_id):
    job = get_job(job_id)
    if not job:
        raise HTTPException(404, 'Asset not found')
    return job


def _filtered(jobs, project='', review_status='', tag='', rights_status='', collection=''):
    for job in jobs:
        meta = AssetMetadata(**job.metadata)
        if project and meta.project != project:
            continue
        if review_status and meta.review_status != review_status:
            continue
        if rights_status and meta.rights_status != rights_status:
            continue
        if tag and tag.casefold() not in {v.casefold() for v in meta.tags}:
            continue
        if collection and collection not in meta.collections:
            continue
        yield job


@router.get('')
async def library(q: str = Query(default='', max_length=500), project: str = '', review_status: str = '',
                  tag: str = '', rights_status: str = '', collection: str = '',
                  sort: str = Query(default='relevance', pattern='^(name|newest|relevance)$'),
                  limit: int = Query(default=200, ge=1, le=500), offset: int = Query(default=0, ge=0)):
    jobs = list_jobs()
    matched = []
    for job in _filtered(jobs, project, review_status, tag, rights_status, collection):
        public = asset_view(job)
        score = search_score(q, [job.filename, public['metadata'], job.summary, job.flash_result, job.deep_results, job.shot_annotations])
        if score >= 0:
            if q:
                matching_shot = next((s for s in shot_views(job) if search_score(q, s) >= 0), None)
                public['match_context'] = matching_shot.get('visual_description', '') if matching_shot else 'Matched asset metadata'
            matched.append((score, public))
    if sort == 'name':
        matched.sort(key=lambda item: item[1]['metadata']['title'].casefold())
    elif sort == 'newest':
        matched.sort(key=lambda item: item[1]['created_at'], reverse=True)
    else:
        matched.sort(key=lambda item: item[0], reverse=True)
    return {'assets': [v for _, v in matched[offset:offset + limit]], 'total': len(matched),
        'facets': {'projects': sorted({j.metadata.get('project') for j in jobs if j.metadata.get('project')}),
                   'tags': sorted({tag for j in jobs for tag in j.metadata.get('tags', [])}),
                   'collections': sorted({v for j in jobs for v in j.metadata.get('collections', [])})},
        'stats': {'assets': len(jobs), 'shots': sum(asset_view(j)['shot_count'] for j in jobs),
                  'reviewed': sum(j.metadata.get('review_status') == 'reviewed' for j in jobs),
                  'duration_seconds': sum(j.technical.get('duration_seconds', 0) for j in jobs)}}


@router.get('/search/shots')
async def search_shots(q: str = Query(default='', max_length=500), project: str = '', review_status: str = '',
                       tag: str = '', rights_status: str = '', collection: str = '',
                       limit: int = Query(default=200, ge=1, le=500), offset: int = Query(default=0, ge=0)):
    matches = []
    for job in _filtered(list_jobs(), project=project, rights_status=rights_status, collection=collection):
        for shot in shot_views(job):
            if review_status and shot['review_status'] != review_status:
                continue
            if tag and tag.casefold() not in {t.casefold() for t in shot['tags']}:
                continue
            score = search_score(q, shot)
            if score >= 0:
                matches.append((score, shot))
    matches.sort(key=lambda item: item[0], reverse=True)
    return {'shots': [s for _, s in matches[offset:offset + limit]], 'total': len(matches), 'search_type': 'keyword'}


@router.get('/{job_id}')
async def asset_detail(job_id: str):
    return asset_view(require_job(job_id), detail=True)


@router.patch('/{job_id}')
async def edit_asset(job_id: str, metadata: AssetMetadata):
    job = require_job(job_id)
    merged = AssetMetadata(**{**job.metadata, **metadata.model_dump(exclude_unset=True)}).model_dump()
    return asset_view(update_job(job_id, metadata=merged), detail=True)


@router.patch('/{job_id}/shots/{shot_number}')
async def edit_shot(job_id: str, shot_number: int, annotation: ShotAnnotation):
    job = require_job(job_id)
    if not any(s['shot_number'] == shot_number for s in shot_views(job)):
        raise HTTPException(404, 'Shot not found')
    key = str(shot_number)
    merged = {**job.shot_annotations.get(key, {}), **annotation.model_dump(exclude_unset=True)}
    update_job(job_id, shot_annotations={**job.shot_annotations, key: ShotAnnotation(**merged).model_dump()})
    return {'shot_number': shot_number, **merged}


@router.get('/{job_id}/media')
async def media(job_id: str):
    job = require_job(job_id)
    if not job.local_path or not Path(job.local_path).is_file():
        raise HTTPException(404, 'Local media is unavailable for this asset')
    # Starlette FileResponse handles HTTP Range for seeking without loading the file into memory.
    return FileResponse(job.local_path, media_type=job.mime_type)


@router.get('/{job_id}/poster')
async def poster(job_id: str):
    require_job(job_id)
    path = Path(settings.upload_dir) / job_id / 'poster.jpg'
    if not path.is_file():
        raise HTTPException(404, 'Poster not available')
    return FileResponse(path, media_type='image/jpeg')


@router.post('/{job_id}/analyze', status_code=202)
async def analyze_asset(job_id: str, body: AnalyzeRequest, api_key: str | None = Depends(get_api_key)):
    require_job(job_id)
    if not (api_key or settings.google_api_key):
        raise HTTPException(400, 'Configure a Gemini key in Settings or GOOGLE_API_KEY in .env to analyze footage')
    if not claim_analysis(job_id):
        raise HTTPException(409, 'This asset is already queued or analyzing')
    start_job(job_id, body, api_key)
    return {'job_id': job_id, 'status': 'analyzing'}


@router.post('/{job_id}/cancel')
async def cancel_analysis(job_id: str):
    require_job(job_id)
    if not cancel_job(job_id):
        raise HTTPException(409, 'There is no active analysis to cancel')
    return {'status': 'cancelling'}


@router.get('/{job_id}/export')
async def export_asset(job_id: str, format: str = Query(default='json', pattern='^(json|csv|xmp|srt|edl|fcpxml)$')):
    from app.services.library_export import export_library
    job = require_job(job_id)
    try:
        content, media_type, extension = export_library(job, format)
    except ValueError as exc:
        raise HTTPException(422, str(exc))
    name = quote(f'{Path(job.filename).stem}_metadata.{extension}')
    return Response(content=content, media_type=media_type,
                    headers={'Content-Disposition': f"attachment; filename*=UTF-8''{name}"})
