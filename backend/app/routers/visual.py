import asyncio
import math

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field, model_validator

from app.routers.library import require_job
from app.services import visual_index
from app.services import composition_index
from app.services import shape_index, shape_geometry
from app.dependencies import get_api_key
from app.config import settings

router = APIRouter(prefix='/api/visual')


class MatchRequest(BaseModel):
    shot_number: int = Field(ge=1)
    seconds: float = Field(ge=0, allow_inf_nan=False)
    revision: str = Field(min_length=1, max_length=100)
    target_ids: list[str] = Field(min_length=1, max_length=20)
    shape: float = Field(default=1, ge=0, le=1, allow_inf_nan=False)
    composition: float = Field(default=1, ge=0, le=1, allow_inf_nan=False)
    color: float = Field(default=1, ge=0, le=1, allow_inf_nan=False)
    region: tuple[float, float, float, float] | None = None
    limit: int = Field(default=12, ge=1, le=48)
    prepare_composition: bool = True
    prepare_shape: bool = True
    source_shape_id: int | None = Field(default=None, ge=0, le=5)
    align_shape: bool = False

    @model_validator(mode='after')
    def valid(self):
        if self.shape + self.composition + self.color <= 0:
            raise ValueError('Enable at least one matching dimension.')
        if self.region:
            x, y, w, h = self.region
            if not all(math.isfinite(v) for v in self.region) or min(x, y) < 0 or min(w, h) < .02 or x + w > 1.001 or y + h > 1.001:
                raise ValueError('Choose a valid region inside the frame.')
        return self


@router.get('/{job_id}/index')
async def index_status(job_id: str):
    try:
        return visual_index.status(require_job(job_id))
    except ValueError as exc:
        raise HTTPException(409, str(exc))


@router.post('/{job_id}/index', status_code=202)
async def start_index(job_id: str):
    try:
        return visual_index.start(require_job(job_id))
    except ValueError as exc:
        raise HTTPException(409, str(exc))


@router.post('/{job_id}/index/cancel')
async def stop_index(job_id: str):
    require_job(job_id)
    await visual_index.stop(job_id)
    return {'status': 'paused'}


@router.get('/{job_id}/frame')
async def get_frame(job_id: str, shot_number: int = Query(ge=1), seconds: float = Query(ge=0, allow_inf_nan=False),
                    revision: str = Query(min_length=1, max_length=100)):
    job = require_job(job_id)
    try:
        key, _ = visual_index.validate_frame(job, shot_number, seconds, revision)
        path = await visual_index.frame(job, key, seconds)
        return FileResponse(path, media_type='image/jpeg')
    except ValueError as exc:
        raise HTTPException(409, str(exc))


class ShapeRequest(BaseModel):
    shot_number: int = Field(ge=1)
    seconds: float = Field(ge=0, allow_inf_nan=False)
    revision: str = Field(min_length=1, max_length=100)


@router.post('/{job_id}/shapes')
async def identify_shapes(job_id: str, body: ShapeRequest, api_key: str | None = Depends(get_api_key)):
    job = require_job(job_id)
    try:
        key, _ = visual_index.validate_frame(job, body.shot_number, body.seconds, body.revision)
        saved = shape_index.cached(job, key).get(round(body.seconds * 1000))
        if (saved is None or saved.get('needs_retry')) and not (api_key or settings.google_api_key):
            raise HTTPException(400, 'Shape identification uses Gemini. Add a key in Settings first.')
        profile = await shape_index.ensure(job, key, body.seconds, api_key)
        visual_index.validate_frame(require_job(job_id), body.shot_number, body.seconds, key)
        return profile
    except ValueError as exc:
        raise HTTPException(409, str(exc))
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(502, 'Shape identification could not finish. Check your Gemini key/quota and try again.')


@router.post('/{job_id}/search')
async def find_matches(job_id: str, body: MatchRequest, api_key: str | None = Depends(get_api_key)):
    job = require_job(job_id)
    targets = [require_job(ident) for ident in dict.fromkeys(body.target_ids)]
    try:
        key, _ = visual_index.validate_frame(job, body.shot_number, body.seconds, body.revision)
        for target in targets:
            visual_index.source_info(target)
        source = await asyncio.to_thread(visual_index.features, await visual_index.frame(job, key, body.seconds))
        if not source['usable']:
            raise ValueError('This frame is nearly blank. Choose a frame with visible detail.')
        source_form = None
        forms = []
        if body.shape:
            shapes = shape_index.cached(job, key).get(round(body.seconds * 1000))
            if body.prepare_shape:
                needs_key = shapes is None or shapes.get('needs_retry')
                for target in targets:
                    state = shape_index.status(target, visual_index.source_info(target)[0])
                    needs_key = needs_key or state['indexed'] < state['total']
                if not (api_key or settings.google_api_key) and needs_key:
                    raise HTTPException(400, 'Shape identification uses Gemini. Add a key in Settings first.')
                shapes = await shape_index.ensure(job, key, body.seconds, api_key)
            forms = shapes['forms'] if shapes else []
            source_form = shape_geometry.select(forms, body.region, body.source_shape_id)
            if body.prepare_shape and source_form is None:
                raise ValueError('No clear silhouette was identified. Choose another frame or use Color or Composition.')
        profile = None
        if body.composition:
            if body.prepare_composition:
                if not (api_key or settings.google_api_key):
                    raise HTTPException(400, 'Composition matching uses Gemini. Add a key in Settings first.')
                profile = await composition_index.ensure(job, key, body.seconds, api_key)
            else:
                # Polls only read saved results: never initiate provider calls or retry failures.
                profile = composition_index.cached(job, key).get(round(body.seconds * 1000))
            if profile and (profile['kind'] == 'unclear' or not profile['focal_point']):
                raise ValueError('No clear focal subject was identified in this frame. Choose another frame or use Shape and Color.')
            if body.prepare_composition:
                for target in targets:
                    composition_index.start(target, api_key)
        if body.shape and body.prepare_shape:
            for target in targets:
                shape_index.start(target, api_key)
        result = await asyncio.to_thread(visual_index.search, source, job_id, body.shot_number, targets,
            {'shape': body.shape, 'composition': body.composition, 'color': body.color}, body.region, body.limit, profile, source_form, body.align_shape)
        result['source_shapes'] = forms
        visual_index.validate_frame(require_job(job_id), body.shot_number, body.seconds, key)
        return result
    except ValueError as exc:
        raise HTTPException(409, str(exc))
    except Exception as exc:
        if isinstance(exc, HTTPException):
            raise
        raise HTTPException(502, 'Gemini visual analysis could not finish. Check your key/quota and try again; saved frames are retained.')
