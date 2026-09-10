import asyncio
import json
import math
from types import SimpleNamespace

import pytest

from app.services import shape_geometry as geometry, shape_index, visual_index
from app.services.library_service import shot_views
from test_visual_matching import visual_asset, wait_index


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
            'shape': 1, 'composition': 0, 'color': 0, 'prepare_shape': False}
    response = client.post(f'/api/visual/{ident}/search', json=body)
    assert response.status_code == 200, response.text
    data = response.json()
    assert len(data['matches']) == 1
    match = data['matches'][0]
    assert match['source_outline'] == data['source_shape']['outline']
    assert match['shape_label'] == 'moon' and match['shape_summary'] == 'wheel → moon'
    assert match['target_outline'] and match['target_box'] is None
    assert client.post(f'/api/visual/{ident}/search', json={**body, 'align_shape': True}).json()['matches'] == []
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
