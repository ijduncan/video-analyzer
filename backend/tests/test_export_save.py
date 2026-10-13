import copy
import io
import zipfile
from pathlib import Path
from unittest.mock import Mock
import xml.etree.ElementTree as ET

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.export_destination import grant, consume, save
from app.services.job_store import update_job, create_job
from app.services.xmp_sidecars import write_sidecars, merge_xmp
from app.services.library_export import NS, export_library
from app import desktop_window


def physical_asset(asset, tmp_path):
    source = tmp_path / 'original video.mov'
    source.write_bytes(b'unchanged original media')
    return update_job(asset.job_id, local_path=str(source), analysis_config={'started_at': 'saved-run'},
                      technical={**asset.technical, 'audio_channels': [2]})


def test_sidecars_merge_preserve_unknown_and_other_marker_tracks_and_backup(asset, tmp_path):
    job = physical_asset(asset, tmp_path)
    sidecar = Path(job.local_path).with_suffix('.xmp')
    old = b'''<x:xmpmeta xmlns:x="adobe:ns:meta/"><rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"><rdf:Description xmlns:custom="urn:custom" xmlns:xmpDM="http://ns.adobe.com/xmp/1.0/DynamicMedia/"><custom:note>Keep me</custom:note><xmpDM:Tracks><rdf:Bag><rdf:li rdf:parseType="Resource"><xmpDM:trackName>Editor markers</xmpDM:trackName></rdf:li></rdf:Bag></xmpDM:Tracks></rdf:Description></rdf:RDF></x:xmpmeta>'''
    sidecar.write_bytes(old)
    source_bytes = Path(job.local_path).read_bytes()
    result = write_sidecars([job])[0]
    assert result['written'] and Path(result['backup']).read_bytes() == old
    root = ET.fromstring(sidecar.read_bytes())
    assert root.findtext('.//{urn:custom}note') == 'Keep me'
    tracks = root.findall('.//xmpDM:trackName', NS)
    assert [item.text for item in tracks] == ['Editor markers', 'Video Analyzer shot estimates']
    assert Path(job.local_path).read_bytes() == source_bytes
    second = write_sidecars([job])[0]
    assert second['written']
    assert len(ET.fromstring(sidecar.read_bytes()).findall('.//xmpDM:trackName', NS)) == 2


def test_invalid_existing_sidecar_and_missing_source_are_not_overwritten(asset, tmp_path):
    job = physical_asset(asset, tmp_path)
    path = Path(job.local_path).with_suffix('.xmp')
    path.write_bytes(b'not valid XMP')
    assert not write_sidecars([job])[0]['written']
    assert path.read_bytes() == b'not valid XMP'
    job.local_path = str(tmp_path / 'offline.mov')
    assert 'offline' in write_sidecars([job])[0]['error']


def test_grants_are_one_use_extension_bound_and_preserve_changed_targets(tmp_path):
    destination = tmp_path / 'timeline.xml'
    destination.write_bytes(b'keep existing')
    ticket = grant(str(destination), 'timeline.xml')['ticket']
    destination.write_bytes(b'changed by editor')
    with pytest.raises(ValueError, match='changed'):
        consume(ticket, 'xml')
    assert destination.read_bytes() == b'changed by editor'
    ticket = grant(str(destination), 'timeline.xml')['ticket']
    path, before = consume(ticket, 'xml')
    save(path, before, b'new export')
    assert destination.read_bytes() == b'new export'
    with pytest.raises(ValueError, match='expired'):
        consume(ticket, 'xml')
    with pytest.raises(ValueError, match='extension'):
        grant(str(tmp_path / 'movie.mov'), 'timeline.xml')


def test_local_save_cancel_relinks_and_optional_sidecars(client, asset, tmp_path, monkeypatch):
    from app import native_picker
    job = physical_asset(asset, tmp_path)
    chosen = tmp_path / 'export elsewhere' / 'timeline.fcpxml'
    chosen.parent.mkdir()
    with TestClient(app, base_url='http://127.0.0.1:8000', client=('127.0.0.1', 50000)) as local:
        picker = Mock(return_value=None)
        monkeypatch.setattr(native_picker, 'choose_save_file', picker)
        assert local.post('/api/local-media/export-destination', json={'filename': 'timeline.fcpxml'}).json()['cancelled']
        assert not Path(job.local_path).with_suffix('.xmp').exists()
        picker.return_value = str(chosen)
        destination = local.post('/api/local-media/export-destination', json={'filename': 'timeline.fcpxml'}).json()
        response = local.post('/api/local-media/save-download', json={'ticket': destination['ticket'],
            'url': f'/api/library/{job.job_id}/export?format=fcpxml', 'write_sidecars': True})
        assert response.status_code == 200, response.text
        result = response.json()
        assert result['saved'] and result['path'] == str(chosen) and result['sidecars'][0]['written']
        xml = ET.fromstring(chosen.read_bytes())
        assert 'original%20video.mov' in xml.find('.//asset/media-rep').get('src')
        assert xml.find('.//asset/media-rep').get('src').startswith('file:///')
        assert Path(job.local_path).read_bytes() == b'unchanged original media'
        assert local.post('/api/local-media/export-destination', json={'filename': 'timeline.fcpxml', 'path': str(chosen)}).status_code == 401
        assert local.post('/api/local-media/export-destination', json={'filename': 'timeline.fcpxml'}, headers={'Origin': 'https://evil.invalid'}).status_code == 403
        assert local.post('/api/local-media/save-download', json={'ticket': 'x', 'url': 'https://evil.invalid'}).status_code == 422


def test_native_save_bridge_trust_and_cancel(monkeypatch):
    import webview
    api = desktop_window.NativeFiles('http://127.0.0.1:8000')
    api._window = Mock(get_current_url=Mock(return_value='http://127.0.0.1:8000'), create_file_dialog=Mock(return_value=None))
    assert api.choose_export_file('timeline.xml') is None
    assert api._window.create_file_dialog.call_args.args[0] == webview.FileDialog.SAVE
    api._window.get_current_url.return_value = 'https://evil.invalid'
    with pytest.raises(ValueError, match='local'):
        api.choose_export_file('timeline.xml')
    with pytest.raises(ValueError):
        grant('/tmp/export.exe', 'export.exe')


def test_batch_save_package_references_originals_and_defaults_to_no_sidecars(client, asset, tmp_path):
    job = physical_asset(asset, tmp_path)
    other = copy.deepcopy(job)
    other.job_id = 'second-media'
    other.local_path = str(tmp_path / 'second.mov')
    Path(other.local_path).write_bytes(b'other original video')
    other = create_job(other)
    destination = tmp_path / 'library.zip'
    request = {'job_ids': [job.job_id, other.job_id], 'format': 'fcpxml', 'include_metadata': True,
               'analysis_versions': {job.job_id: 'saved-run', other.job_id: 'saved-run'}}
    with TestClient(app, base_url='http://127.0.0.1:8000', client=('127.0.0.1', 50000)) as local:
        body = {'ticket': grant(str(destination), 'library.zip')['ticket'],
                'url': '/api/library/media-export', 'media': request}
        response = local.post('/api/local-media/save-download', json=body)
        assert response.status_code == 200, response.text
        assert response.json()['sidecars'] == []
        with zipfile.ZipFile(io.BytesIO(destination.read_bytes())) as package:
            root = ET.fromstring(package.read('Video Analyzer.fcpxml'))
            references = root.findall('.//asset/media-rep')
            assert len(references) == 2 and all(node.get('src').startswith('file:///') for node in references)
            assert len([name for name in package.namelist() if name.endswith('.xmp')]) == 2
        assert not Path(job.local_path).with_suffix('.xmp').exists()
        request['analysis_versions'][job.job_id] = 'old-run'
        body.update(ticket=grant(str(tmp_path / 'stale.zip'), 'stale.zip')['ticket'], write_sidecars=True)
        assert local.post('/api/local-media/save-download', json=body).status_code == 409
        assert not (tmp_path / 'stale.zip').exists()
        assert not Path(job.local_path).with_suffix('.xmp').exists()


def test_sidecar_collision_and_scalar_attribute_merge(asset, tmp_path):
    job = physical_asset(asset, tmp_path)
    Path(job.local_path).with_suffix('.mp4').write_bytes(b'different video sharing stem')
    assert 'Another video' in write_sidecars([job])[0]['error']
    assert not Path(job.local_path).with_suffix('.xmp').exists()
    old = b'''<x:xmpmeta xmlns:x="adobe:ns:meta/"><rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"><rdf:Description xmlns:xmpDM="http://ns.adobe.com/xmp/1.0/DynamicMedia/" xmpDM:director="Former director"/></rdf:RDF></x:xmpmeta>'''
    new = b'''<x:xmpmeta xmlns:x="adobe:ns:meta/"><rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"><rdf:Description xmlns:xmpDM="http://ns.adobe.com/xmp/1.0/DynamicMedia/"><xmpDM:director>New director</xmpDM:director></rdf:Description></rdf:RDF></x:xmpmeta>'''
    result = ET.fromstring(merge_xmp(old, new))
    description = result.find('.//rdf:Description', NS)
    assert f"{{{NS['xmpDM']}}}director" not in description.attrib
    assert description.findtext('xmpDM:director', namespaces=NS) == 'New director'
