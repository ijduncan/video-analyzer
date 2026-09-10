import asyncio
import json
from types import SimpleNamespace

import pytest

from app.services import composition_index as composition, visual_index
from app.services.library_service import shot_views
from app.services.adaptive_concurrency import AdaptiveConcurrency
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


def save_profiles(asset, key, entries):
    db = composition.db_for(asset, key)
    try:
        db.executemany('INSERT OR REPLACE INTO composition VALUES (?,?,?)', [
            (composition.version(), round(s * 1000), json.dumps(profile(str(round(s * 1000))))) for s in entries])
        db.commit()
    finally:
        db.close()


def test_parallel_composition_preserves_cache_and_does_not_repeat_frames(client, visual_asset, monkeypatch):
    client.post(f'/api/visual/{visual_asset.job_id}/index')
    state = wait_index(client, visual_asset.job_id)
    key = state['revision']
    calls = []
    active = peak = 0

    async def verify():
        nonlocal active, peak
        monkeypatch.setattr(composition, '_background_gate', AdaptiveConcurrency(2))
        monkeypatch.setattr(composition.settings, 'composition_index_concurrency', 2)
        started, release = asyncio.Event(), asyncio.Event()

        async def generate(asset, revision, entries, api_key, **kwargs):
            nonlocal active, peak
            active += 1
            peak = max(peak, active)
            calls.extend(entries)
            if active == 2:
                started.set()
            try:
                await release.wait()
                save_profiles(asset, revision, entries)
            finally:
                active -= 1

        monkeypatch.setattr(composition, 'generate', generate)
        task = asyncio.create_task(composition.build(visual_asset, key, None))
        try:
            await asyncio.wait_for(started.wait(), 2)
        finally:
            release.set()
            await task
        assert peak == 2 and active == 0
        assert len(calls) == len(set(calls)) == state['composition']['total']
        assert composition.status(visual_asset, key)['indexed'] == state['composition']['total']
        await composition.build(visual_asset, key, None)
        assert len(calls) == state['composition']['total']

    asyncio.run(verify())


def test_interactive_composition_shares_inflight_frame(client, visual_asset, monkeypatch):
    key, _ = visual_index.source_info(visual_asset)
    calls = []

    async def verify():
        started, release = asyncio.Event(), asyncio.Event()

        async def generate(asset, revision, entries, api_key, **kwargs):
            calls.append(entries)
            started.set()
            await release.wait()
            save_profiles(asset, revision, entries)

        monkeypatch.setattr(composition, 'generate', generate)
        background = asyncio.create_task(composition.ensure_batch(visual_asset, key, [1.5, 1.6]))
        await started.wait()
        interactive = asyncio.create_task(composition.ensure(visual_asset, key, 1.5))
        await asyncio.sleep(0)
        assert not interactive.done()
        release.set()
        await asyncio.gather(background, interactive)
        assert calls == [[1.5, 1.6]]

    asyncio.run(verify())


def test_pause_cancels_every_composition_worker(client, visual_asset, monkeypatch):
    client.post(f'/api/visual/{visual_asset.job_id}/index')
    key = wait_index(client, visual_asset.job_id)['revision']
    active = 0

    async def verify():
        nonlocal active
        monkeypatch.setattr(composition, '_background_gate', AdaptiveConcurrency(2))
        monkeypatch.setattr(composition.settings, 'composition_index_concurrency', 2)
        started = asyncio.Event()

        async def generate(*args, **kwargs):
            nonlocal active
            active += 1
            if active == 2:
                started.set()
            try:
                await asyncio.Event().wait()
            finally:
                active -= 1

        monkeypatch.setattr(composition, 'generate', generate)
        task = asyncio.create_task(composition.build(visual_asset, key, None))
        composition._tasks[visual_asset.job_id] = task
        try:
            await asyncio.wait_for(started.wait(), 2)
        finally:
            await composition.stop(visual_asset.job_id)
        assert task.cancelled() and active == 0
        assert composition._background_gate.active == 0

    asyncio.run(verify())
