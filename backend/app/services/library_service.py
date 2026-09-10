"""Searchable public asset views, separate from private storage/provider fields."""
import json
import re
from datetime import datetime
from pathlib import Path
from urllib.parse import quote
from app.config import settings
from app.models.library import AssetMetadata


def seconds(value: str) -> float:
    try:
        total = 0.0
        for part in str(value).split(':'):
            total = total * 60 + float(part)
        return total
    except ValueError:
        return 0.0


def thumbnail_url(job, number):
    thumb = Path(settings.upload_dir) / job.job_id / 'thumbs' / f'shot_{number}.jpg'
    if not thumb.is_file():
        return None
    started = job.analysis_config.get('started_at')
    if started:
        try:
            # A stale file must never illustrate a different interval during reanalysis.
            if thumb.stat().st_mtime < datetime.fromisoformat(started).timestamp():
                return None
        except (ValueError, TypeError, OSError):
            return None
    version = quote(str(started or thumb.stat().st_mtime_ns), safe='')
    return f'/api/thumbnails/{job.job_id}/{number}?v={version}'


def asset_view(job, detail=False):
    metadata = AssetMetadata(**job.metadata).model_dump()
    if not metadata['title']:
        metadata['title'] = Path(job.filename).stem
    poster = Path(settings.upload_dir) / job.job_id / 'poster.jpg'
    view = {
        'job_id': job.job_id, 'filename': job.filename, 'status': job.status,
        'created_at': job.created_at.isoformat(), 'size_bytes': job.size_bytes,
        'mime_type': job.mime_type, 'youtube_url': job.youtube_url,
        'metadata': metadata, 'technical': job.technical,
        'shot_count': sum(len(scene.get('shots', [])) for scene in (job.flash_result or {}).get('scenes', [])),
        'summary': (job.summary or {}).get('executive_summary', ''),
        'thumbnail_url': f'/api/library/{job.job_id}/poster' if poster.is_file() else None,
        'preview_url': f'/api/library/{job.job_id}/media' if job.local_path else None,
        'progress': job.progress, 'error': job.error, 'warnings': job.warnings,
        'analysis_progress': job.analysis_progress,
    }
    if detail:
        view.update(flash=job.flash_result, deep=job.deep_results, video_summary=job.summary,
                    custom_result=job.custom_result, shot_matches=job.shot_matches,
                    analysis_config=job.analysis_config, shot_annotations=job.shot_annotations,
                    transcript=job.transcript, cost_estimate=job.cost_estimate)
        view['analysis_history'] = job.analysis_history
        if job.flash_result:
            view['flash'] = {**job.flash_result, 'scenes': [
                {**scene, 'shots': [{**shot, 'thumbnail_url': thumbnail_url(job, shot.get('shot_number', 0))}
                                    for shot in scene.get('shots', [])]}
                for scene in job.flash_result.get('scenes', [])
            ]}
    return view


def search_score(query: str, data) -> int:
    """Explainable case-insensitive keyword matching; deliberately not called semantic search."""
    terms = re.findall(r'\w+', query.casefold())
    def content(value):
        if isinstance(value, dict):
            return ' '.join(content(item) for item in value.values())
        if isinstance(value, (list, tuple)):
            return ' '.join(content(item) for item in value)
        return value if isinstance(value, str) else ''
    text = content(data).casefold()
    if not all(term in text for term in terms):
        return -1
    return sum(min(text.count(term), 20) for term in terms)


def shot_views(job):
    for scene in (job.flash_result or {}).get('scenes', []):
        for shot in scene.get('shots', []):
            number = shot.get('shot_number', 0)
            annotation = job.shot_annotations.get(str(number), {})
            yield {
                **shot, 'job_id': job.job_id, 'filename': job.filename,
                'scene_number': scene.get('scene_number'), 'scene_title': scene.get('scene_title', ''),
                'start_seconds': seconds(shot.get('start_time', '0')),
                'end_seconds': seconds(shot.get('end_time', '0')),
                'tags': list(dict.fromkeys(shot.get('tags', []) + annotation.get('tags', []))),
                'human_tags': annotation.get('tags', []), 'notes': annotation.get('notes', ''),
                'review_status': annotation.get('review_status', 'unreviewed'),
                'thumbnail_url': thumbnail_url(job, number),
                'preview_url': f'/api/library/{job.job_id}/media' if job.local_path else None,
            }
