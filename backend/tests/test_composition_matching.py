import asyncio
import json
from types import SimpleNamespace

import pytest

from app.services import composition_index as composition, visual_index
from app.services.library_service import shot_views
from test_visual_matching import visual_asset, wait_index


def profile(ident='1000', x=725, facing='left', space='left', kind='person'):
    return {'frame_id': ident, 'kind': kind, 'subject': 'principal subject',
            'subject_box': [30, max(0, x-220), 990, min(1000, x+220)], 'focal_point': [x, 238],
            'facing': facing, 'open_space': space, 'framing': 'medium', 'principal_count': 1,
            'summary': f'Subject at {x}, facing {facing}, open space {space}.'}


def test_composition_rewards_subject_and_lead_room_not_random_detail():
    source = profile()
    same = composition.compare(source, profile(x=710))['score']
    centered = composition.compare(source, profile(x=500, facing='front', space='balanced'))['score']
    left = composition.compare(source, profile(x=220, facing='right', space='right'))['score']
    assert same > .9
    assert centered < .60
    assert left < .30
    assert composition.compare(source, profile(kind='landscape')) is None
    assert composition.compare(source, profile(kind='object')) is None
    assert composition.compare(source, profile(kind='unclear')) is None
    assert composition.compare(source, profile(x=710))['reasons'] == ['Subject right', 'Open space left', 'Facing left']


def test_profile_rejects_invalid_geometry():
    for change in [{'subject_box': [0, 0, 0, 10]}, {'focal_point': [2000, 0]}, {'focal_point': [float('nan'), 0]}, {'subject_box': None}]:
        with pytest.raises(ValueError):
            composition.Profile.model_validate({**profile(), **change})


def test_api_search_uses_cached_semantics_and_never_calls_provider_when_polling(client, visual_asset, monkeypatch):
    ident = visual_asset.job_id
    client.post(f'/api/visual/{ident}/index')
    state = wait_index(client, ident)
    key = state['revision']
    db = composition.db_for(visual_asset, key)
    try:
        db.execute('INSERT INTO composition VALUES (?,?,?)', (composition.version(), 1500, json.dumps(profile('1500'))))
        for shot, seconds, _ in visual_index.samples(list(shot_views(visual_asset))):
            if shot['shot_number'] == 2:
                db.execute('INSERT INTO composition VALUES (?,?,?)', (composition.version(), round(seconds*1000), json.dumps(profile(str(round(seconds*1000)), x=700))))
        db.commit()
    finally:
        db.close()
    async def no_provider(*args, **kwargs):
        pytest.fail('Polling must not initiate paid analysis')
    monkeypatch.setattr(composition, 'generate', no_provider)
    result = client.post(f'/api/visual/{ident}/search', json={'shot_number': 1, 'seconds': 1.5, 'revision': key,
        'target_ids': [ident], 'shape': 0, 'composition': 1, 'color': 0, 'prepare_composition': False})
    assert result.status_code == 200, result.text
    body = result.json()
    assert len(body['matches']) == 1
    candidate = body['matches'][0]
    assert candidate['box_basis'] == 'Gemini dominant subject'
    assert candidate['source_box'] == composition.xywh(profile('1500'))
    assert 'Subject right' in candidate['reasons']
    assert body['source_composition']['summary'] == profile('1500')['summary']


def test_no_semantics_never_falls_back_to_contours(client, visual_asset):
    ident = visual_asset.job_id
    client.post(f'/api/visual/{ident}/index')
    state = wait_index(client, ident)
    body = {'shot_number': 1, 'seconds': 1.5, 'revision': state['revision'], 'target_ids': [ident],
            'shape': 0, 'composition': 1, 'color': 0, 'prepare_composition': False}
    result = client.post(f'/api/visual/{ident}/search', json=body)
    assert result.status_code == 200
    assert result.json()['matches'] == []
    assert client.post(f'/api/visual/{ident}/search', json={**body, 'prepare_composition': True}).status_code == 400


def test_profile_cache_and_usage_survive_repeated_source_requests(client, visual_asset, monkeypatch):
    calls = []
    async def generate_content(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(text=json.dumps({'frames': [profile('1500')]}), candidates=[], usage_metadata=None)
    fake = SimpleNamespace(aio=SimpleNamespace(models=SimpleNamespace(generate_content=generate_content)))
    monkeypatch.setattr(composition, 'get_client', lambda key: fake)
    key, _ = visual_index.source_info(visual_asset)
    async def check():
        a = await composition.ensure(visual_asset, key, 1.5, 'fixture')
        b = await composition.ensure(visual_asset, key, 1.5, 'fixture')
        assert a == b
    asyncio.run(check())
    assert len(calls) == 1
    assert composition.status(visual_asset, key)['requests'] == 1


def test_incomplete_response_records_usage_without_publishing_profiles(client, visual_asset, monkeypatch):
    async def generate_content(**kwargs):
        return SimpleNamespace(text=json.dumps({'frames': []}), candidates=[], usage_metadata=None)
    fake = SimpleNamespace(aio=SimpleNamespace(models=SimpleNamespace(generate_content=generate_content)))
    monkeypatch.setattr(composition, 'get_client', lambda key: fake)
    key, _ = visual_index.source_info(visual_asset)
    with pytest.raises(ValueError, match='every requested frame'):
        asyncio.run(composition.ensure(visual_asset, key, 1.5, 'fixture'))
    assert composition.cached(visual_asset, key) == {}
    assert composition.status(visual_asset, key)['requests'] == 1
