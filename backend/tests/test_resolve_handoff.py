import base64
import copy
import io
import json
import zipfile

import pytest
from app.services.editor_bridge import source_fingerprint
from app.services.media_export import build_download
from app.services.resolve_handoff import prepare_import, finish_import


def package(asset,tmp_path):
    job=copy.deepcopy(asset)
    original=tmp_path/'Original.mov'; original.write_bytes(b'original bytes never rewritten')
    job.local_path=str(original);job.source_fingerprint=source_fingerprint(original)[0]
    job.technical.update(audio_channels=[2],audio_sample_rates=[48000])
    path=build_download([job],'Acceptance','timeline',True)
    try:return path.read_bytes(),original
    finally:path.unlink()


def test_prepared_package_uses_complete_mapping_and_owned_temporary_xml(asset,tmp_path):
    data,original=package(asset,tmp_path)
    pack=prepare_import(base64.b64encode(data).decode())
    from pathlib import Path
    xml=Path(pack['timeline_path'])
    try:
        assert xml.is_file() and 'xmeml' in xml.read_text()
        assert pack['assets'][0]['media_path']==str(original)
        assert pack['assets'][0]['metadata']['record']['analysis']['flash_result']['total_shots']==2
        assert 'private-provider' not in json.dumps(pack)
    finally:finish_import(pack['import_id'])
    assert not xml.exists() and original.read_bytes()==b'original bytes never rewritten'


def test_changed_source_is_rejected_before_native_import(asset,tmp_path):
    data,original=package(asset,tmp_path); original.write_bytes(b'changed original')
    with pytest.raises(ValueError,match='changed since export'):prepare_import(base64.b64encode(data).decode())


def test_missing_source_or_mismatched_xml_cannot_be_imported(asset,tmp_path):
    data,original=package(asset,tmp_path)
    with zipfile.ZipFile(io.BytesIO(data)) as old:
        buffer=io.BytesIO()
        with zipfile.ZipFile(buffer,'w') as new:
            for name in ('Resolve handoff.json','Video Analyzer.xml'):
                value=old.read(name)
                if name.endswith('.xml'):value=value.replace(b'Original.mov',b'Another.mov')
                new.writestr(name,value)
    with pytest.raises(ValueError,match='do not match'):prepare_import(base64.b64encode(buffer.getvalue()).decode())
    original.unlink()
    with pytest.raises(ValueError,match='online'):prepare_import(base64.b64encode(data).decode())


def test_package_endpoint_requires_authenticated_local_editor(client,asset,tmp_path):
    from fastapi.testclient import TestClient
    from app.main import app
    from app.services.editor_bridge import get_pairing_token
    data,_=package(asset,tmp_path);body={'archive':base64.b64encode(data).decode()}
    local=TestClient(app,client=('127.0.0.1',52000))
    assert local.post('/api/editor/resolve/imports/prepare',json=body).status_code==401
    headers={'Authorization':'Bearer '+get_pairing_token()}
    response=local.post('/api/editor/resolve/imports/prepare',json=body,headers=headers)
    assert response.status_code==200,response.text
    assert local.delete('/api/editor/resolve/imports/'+response.json()['import_id'],headers=headers).status_code==200
