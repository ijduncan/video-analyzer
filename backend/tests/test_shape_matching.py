import asyncio
import json
import math
from types import SimpleNamespace

import pytest

from app.services import shape_geometry as geometry, shape_index, visual_index
from app.services.library_service import shot_views
from test_visual_matching import visual_asset, wait_index


def test_priority_reaches_similar_later_shots_first_without_losing_diversity():
    from app.services.visual_features import describe
    from test_visual_matching import picture
    source = describe(picture())
    unrelated = describe(picture(circle=False, center=(60, 50)))
    different_color = describe(picture(color=(255, 150, 0)))
    rows = [(1, 1., unrelated), (1, 2., unrelated), (62, 171., source),
            (62, 172., source), (65, 183., source), (90, 230., different_color)]
    ordered = shape_index.prioritize(rows, source)
    assert ordered[:2] == [171., 183.]
    assert set(ordered) == {row[1] for row in rows}
    assert len(ordered) == len(rows)
    assert ordered.index(230.) < ordered.index(172.)  # One frame per shot before refinements.


def test_running_shape_queue_accepts_new_priority_without_restarting(client, visual_asset):
    from app.services.visual_features import describe
    from test_visual_matching import picture
    client.post(f'/api/visual/{visual_asset.job_id}/index')
    state = wait_index(client, visual_asset.job_id)
    task = SimpleNamespace(done=lambda: False)
    shape_index._tasks[visual_asset.job_id] = task
    try:
        shape_index.start(visual_asset, source=describe(picture(color=(255, 150, 0))))
        assert shape_index._tasks[visual_asset.job_id] is task
        assert shape_index._priorities[visual_asset.job_id][0] > 3.5
        assert len(shape_index._priorities[visual_asset.job_id]) == state['shape']['total']
    finally:
        shape_index._tasks.pop(visual_asset.job_id, None)
        shape_index._priorities.pop(visual_asset.job_id, None)


def circle(label='wheel', x=500, y=500, radius=150, aspect=16/9):
    return geometry.describe({'label': label, 'outline': [
        [x+radius*math.cos(i*math.pi/16)/aspect, y+radius*math.sin(i*math.pi/16)] for i in range(32)]}, aspect)


def rectangle():
    return geometry.describe({'label': 'doorway', 'outline': [[300, 250], [700, 250], [700, 750], [300, 750]]}, 16/9)


def test_cross_object_shape_is_independent_of_position_size_label_and_aspect():
    source = circle()
    moved = circle('moon', x=750, y=250, radius=90)
    same = geometry.compare(source, moved)
    assert same['silhouette'] > .96
    assert same['position'] < .5 and same['scale'] < .5
    assert geometry.compare(source, moved, align=True) is None
    assert geometry.compare(source, circle('eye', aspect=9/16))['silhouette'] > .96
    assert geometry.compare(source, rectangle()) is None
    assert geometry.compare(source, circle('lens'), align=True)['score'] > .96


def test_one_source_is_locked_before_candidates_are_scored():
    forms = [rectangle(), circle()]
    assert geometry.select(forms) is forms[0]
    assert geometry.select(forms, form_id=1) is forms[1]
    assert geometry.select(forms, circle()['box']) is forms[1]
    assert geometry.compare(geometry.select(forms), circle('moon')) is None
    with pytest.raises(ValueError, match='fits that region'):
        geometry.select(forms, [0, 0, .03, .03])
    with pytest.raises(ValueError):
        geometry.select(forms, form_id=3)


@pytest.mark.parametrize('outline', [
    [[0, 0], [1000, 1000], [1000, 0], [0, 1000]],
    [[0, 0], [0, 1], [1, 1]],
    [[0, 0], [1001, 0], [100, 100]],
    [[0, 0], [100, float('nan')], [100, 100]],
])
def test_invalid_silhouettes_rejected(outline):
    with pytest.raises(ValueError):
        geometry.Form(label='invalid', outline=outline)


def seed(asset, key):
    db = shape_index.db_for(asset, key)
    entries = [(1500, [circle()])]
    entries += [(round(seconds*1000), [circle('moon', x=730, radius=90)])
                for shot, seconds, _ in visual_index.samples(list(shot_views(asset))) if shot['shot_number'] == 2]
    for millis, forms in entries:
        db.execute('INSERT OR REPLACE INTO shape VALUES (?,?,?)',
                   (shape_index.version(), millis, json.dumps({'frame_id': str(millis), 'forms': forms})))
    db.commit()
    db.close()


def test_api_uses_fixed_silhouettes_and_polling_never_calls_provider(client, visual_asset, monkeypatch):
    ident = visual_asset.job_id
    client.post(f'/api/visual/{ident}/index')
    state = wait_index(client, ident)
    seed(visual_asset, state['revision'])
    async def forbidden(*args, **kwargs):
        pytest.fail('Polling must never call Gemini')
    monkeypatch.setattr(shape_index, 'generate', forbidden)
    body = {'shot_number': 1, 'seconds': 1.5, 'revision': state['revision'], 'target_ids': [ident],
            'shape': 1, 'composition': 0, 'color': 0, 'prepare_shape': False, 'align_shape': False}
    response = client.post(f'/api/visual/{ident}/search', json=body)
    assert response.status_code == 200, response.text
    data = response.json()
    assert len(data['matches']) == 1
    match = data['matches'][0]
    assert match['source_outline'] == data['source_shape']['outline']
    assert match['shape_label'] == 'moon' and match['shape_summary'] == 'wheel → moon'
    assert match['target_outline'] and match['target_box'] is None
    assert client.post(f'/api/visual/{ident}/search', json={**body, 'align_shape': True}).json()['matches'] == []
    default_body = {k: v for k, v in body.items() if k != 'align_shape'}
    assert client.post(f'/api/visual/{ident}/search', json=default_body).json()['matches'] == []
    assert client.post(f'/api/visual/{ident}/search', json={**body, 'region': [0, 0, .03, .03]}).status_code == 409
    assert client.post(f'/api/visual/{ident}/search', json={**body, 'source_shape_id': 5}).status_code == 409


def test_missing_shapes_do_not_fall_back_to_random_contours(client, visual_asset):
    ident = visual_asset.job_id
    client.post(f'/api/visual/{ident}/index')
    state = wait_index(client, ident)
    body = {'shot_number': 1, 'seconds': 1.5, 'revision': state['revision'], 'target_ids': [ident],
            'shape': 1, 'composition': 0, 'color': 0, 'prepare_shape': False}
    assert client.post(f'/api/visual/{ident}/search', json=body).json()['matches'] == []
    assert client.post(f'/api/visual/{ident}/search', json={**body, 'prepare_shape': True}).status_code == 400


def test_identification_cache_usage_and_source_revision(client, visual_asset, monkeypatch):
    calls = []
    async def generate_content(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(text=json.dumps({'frames': [{'frame_id': '1500', 'forms': [
            {'label': 'wheel', 'outline': [[round(x), round(y)] for x, y in circle()['outline']]}]}]}), candidates=[], usage_metadata=None)
    monkeypatch.setattr(shape_index, 'get_client', lambda _: SimpleNamespace(aio=SimpleNamespace(models=SimpleNamespace(generate_content=generate_content))))
    key, _ = visual_index.source_info(visual_asset)
    body = {'shot_number': 1, 'seconds': 1.5, 'revision': key}
    url = f'/api/visual/{visual_asset.job_id}/shapes'
    assert client.post(url, json=body, headers={'X-API-Key': 'fixture'}).status_code == 200
    assert client.post(url, json=body).status_code == 200  # Saved results need no key.
    assert len(calls) == 1 and shape_index.status(visual_asset, key)['requests'] == 1
    assert client.post(url, json={**body, 'revision': 'old'}).status_code == 409


def test_incomplete_output_records_usage_without_publishing(client, visual_asset, monkeypatch):
    async def generate_content(**kwargs):
        return SimpleNamespace(text='{"frames": []}', candidates=[], usage_metadata=None)
    monkeypatch.setattr(shape_index, 'get_client', lambda _: SimpleNamespace(aio=SimpleNamespace(models=SimpleNamespace(generate_content=generate_content))))
    key, _ = visual_index.source_info(visual_asset)
    with pytest.raises(ValueError, match='every requested frame'):
        asyncio.run(shape_index.ensure(visual_asset, key, 1.5, 'fixture'))
    assert shape_index.cached(visual_asset, key) == {}
    assert shape_index.status(visual_asset, key)['requests'] == 1


def test_bad_outline_does_not_discard_valid_shapes_and_all_bad_frames_can_retry(client, visual_asset, monkeypatch):
    valid = {'label': 'doorway', 'outline': [[300, 250], [700, 250], [700, 750], [300, 750]]}
    bad = {'label': 'bad', 'outline': [[0, 0], [1000, 1000], [1000, 0], [0, 1000]]}
    responses = [[bad, valid], [bad], [valid]]
    async def generate_content(**kwargs):
        millis = '1500' if len(responses) == 3 else '1600'
        return SimpleNamespace(text=json.dumps({'frames': [{'frame_id': millis, 'forms': responses.pop(0)}]}), candidates=[], usage_metadata=None)
    monkeypatch.setattr(shape_index, 'get_client', lambda _: SimpleNamespace(aio=SimpleNamespace(models=SimpleNamespace(generate_content=generate_content))))
    key, _ = visual_index.source_info(visual_asset)
    async def verify():
        a = await shape_index.ensure(visual_asset, key, 1.5, 'fixture')
        assert [f['label'] for f in a['forms']] == ['doorway']
        assert a['rejected_forms'] == 1
        with pytest.raises(ValueError, match='No usable outlines'):
            await shape_index.ensure(visual_asset, key, 1.6, 'fixture')
        assert shape_index.cached(visual_asset, key)[1600]['needs_retry']
        b = await shape_index.ensure(visual_asset, key, 1.6, 'fixture')
        assert not b['needs_retry']
    asyncio.run(verify())
    assert shape_index.status(visual_asset, key)['requests'] == 3


def save_empty_profiles(asset, key, entries):
    db = shape_index.db_for(asset, key)
    try:
        db.executemany('INSERT OR REPLACE INTO shape VALUES (?,?,?)', [
            (shape_index.version(), round(s * 1000), json.dumps({'forms': []})) for s in entries])
        db.commit()
    finally:
        db.close()


def test_parallel_batches_publish_once_and_resume_without_rebilling(client, visual_asset, monkeypatch):
    client.post(f'/api/visual/{visual_asset.job_id}/index')
    state = wait_index(client, visual_asset.job_id)
    key = state['revision']
    calls, active, peak = [], 0, 0

    async def verify():
        nonlocal active, peak
        monkeypatch.setattr(shape_index, '_background_gate', asyncio.Semaphore(3))
        monkeypatch.setattr(shape_index.settings, 'shape_index_concurrency', 3)
        started, release = asyncio.Event(), asyncio.Event()

        async def generate(asset, revision, entries, api_key, **kwargs):
            nonlocal active, peak
            calls.extend(entries)
            active += 1
            peak = max(peak, active)
            if active == 3:
                started.set()
            try:
                await release.wait()
                save_empty_profiles(asset, revision, entries)
            finally:
                active -= 1

        monkeypatch.setattr(shape_index, 'generate', generate)
        task = asyncio.create_task(shape_index.build(visual_asset, key, None))
        try:
            await asyncio.wait_for(started.wait(), 2)
        finally:
            release.set()
            await task
        assert peak == 3 and active == 0
        assert len(calls) == len(set(calls)) == state['shape']['total']
        assert shape_index.status(visual_asset, key)['indexed'] == state['shape']['total']
        await shape_index.build(visual_asset, key, None)
        assert len(calls) == state['shape']['total']

    asyncio.run(verify())


def test_interactive_request_joins_overlapping_background_frame(client, visual_asset, monkeypatch):
    key, _ = visual_index.source_info(visual_asset)
    calls = []

    async def verify():
        started, release = asyncio.Event(), asyncio.Event()

        async def generate(asset, revision, entries, api_key, **kwargs):
            calls.append(entries)
            started.set()
            await release.wait()
            save_empty_profiles(asset, revision, entries)

        monkeypatch.setattr(shape_index, 'generate', generate)
        background = asyncio.create_task(shape_index.ensure_batch(visual_asset, key, [1.5, 1.6]))
        await started.wait()
        interactive = asyncio.create_task(shape_index.ensure(visual_asset, key, 1.5))
        await asyncio.sleep(0)
        assert not interactive.done()
        release.set()
        await asyncio.gather(background, interactive)
        assert calls == [[1.5, 1.6]]

    asyncio.run(verify())


def test_pause_cancels_all_parallel_workers(client, visual_asset, monkeypatch):
    client.post(f'/api/visual/{visual_asset.job_id}/index')
    key = wait_index(client, visual_asset.job_id)['revision']
    active = 0

    async def verify():
        nonlocal active
        monkeypatch.setattr(shape_index, '_background_gate', asyncio.Semaphore(3))
        monkeypatch.setattr(shape_index.settings, 'shape_index_concurrency', 3)
        started = asyncio.Event()

        async def generate(*args, **kwargs):
            nonlocal active
            active += 1
            if active == 3:
                started.set()
            try:
                await asyncio.Event().wait()
            finally:
                active -= 1

        monkeypatch.setattr(shape_index, 'generate', generate)
        task = asyncio.create_task(shape_index.build(visual_asset, key, None))
        shape_index._tasks[visual_asset.job_id] = task
        try:
            await asyncio.wait_for(started.wait(), 2)
        finally:
            await shape_index.stop(visual_asset.job_id)
        assert task.cancelled() and active == 0

    asyncio.run(verify())


def test_throttling_backs_off_and_records_successful_usage(client, visual_asset, monkeypatch):
    key, _ = visual_index.source_info(visual_asset)
    attempts, delays = [], []

    class Throttled(Exception):
        code = 429

    async def generate_content(**kwargs):
        attempts.append(kwargs)
        if len(attempts) == 1:
            raise Throttled()
        return SimpleNamespace(text='{"frames":[{"frame_id":"1500","forms":[]}]}', candidates=[], usage_metadata=None)

    async def backoff(delay):
        delays.append(delay)

    asyncio.run(visual_index.frame(visual_asset, key, 1.5))
    monkeypatch.setattr(shape_index, 'get_client', lambda _: SimpleNamespace(aio=SimpleNamespace(models=SimpleNamespace(generate_content=generate_content))))
    monkeypatch.setattr(shape_index.asyncio, 'sleep', backoff)
    asyncio.run(shape_index.ensure(visual_asset, key, 1.5, 'fixture'))
    assert len(attempts) == 2 and delays == [2]
    assert shape_index.status(visual_asset, key)['requests'] == 1
