"""Native Resolve CSV matching and complete metadata retention; no provider calls."""
import copy
import csv
import io
import json
import zipfile

from app.services.editor_metadata import editor_metadata
from app.services.media_export import build_download
from app.services.resolve_metadata_csv import export_resolve_metadata, source_directory


def rows(data):
    assert data.startswith((b'\xff\xfe', b'\xfe\xff'))
    return list(csv.DictReader(io.StringIO(data.decode('utf-16'), newline='')))


def test_native_fields_unicode_dialogue_and_full_record(asset):
    job = copy.deepcopy(asset)
    job.local_path = r'\\server\Footage folder\source.mxf'
    job.metadata['notes'] = 'A visitor says "Olá".\nSecond line.'
    job.transcript = [{'start_time': '00:01', 'end_time': '00:02', 'speaker': 'Visitor', 'text': '你好, booth!'}]
    job.flash_result['scenes'][0]['shots'][0]['slates'] = [{'cinematographer': 'C. WESTERVELT',
        'director': 'I. DUNCAN', 'scene': '9A', 'take': '1', 'production_title': 'Freeman Chronicles'}]
    row, = rows(export_resolve_metadata([job]))
    assert row['File Name'] == 'source.mxf'  # Original name, not display title.
    assert row['Clip Directory'] == r'\\server\Footage folder'
    assert row['DOP'] == 'C. WESTERVELT'
    assert row['Scene'] == '9A' and row['Take'] == '1'
    assert row['Director'] == 'I. DUNCAN'
    assert row['Production Name'] == 'Freeman Chronicles'
    assert row['Description'] == job.metadata['notes']
    assert '你好, booth!' in row['Dialog Notes']
    assert 'A sailboat crosses blue water' in row['Comments']
    assert 'Hands tighten a rope' in row['Comments']
    record = json.loads(row['Comments'].split('[Video Analyzer analysis]\n')[1].split('\n[/Video Analyzer analysis]')[0])
    assert record == editor_metadata(job, include_record=True)['record']
    assert 'private-provider' not in row['Comments']


def test_native_directory_identification():
    assert source_directory('C:/Footage/source.mp4') == r'C:\Footage'
    assert source_directory('//server/share/source.mxf') == r'\\server\share'
    assert source_directory('/Volumes/Footage/source.mov') == '/Volumes/Footage'


def test_duplicate_names_use_selected_source_csv_not_bulk_match(asset):
    jobs = [copy.deepcopy(asset) for _ in range(3)]
    for index, job in enumerate(jobs):
        job.job_id = f'asset-{index}'
        job.local_path = f'C:/Footage/{index}/' + ('same.mov' if index < 2 else 'unique.mov')
        job.analysis_config = {'started_at': 'saved'}
        job.technical.update(audio_channels=[2], audio_sample_rates=[48000])
    path = build_download(jobs, 'Selection', 'timeline', True)
    try:
        with zipfile.ZipFile(path) as archive:
            assert [row['File Name'] for row in rows(archive.read('Resolve metadata.csv'))] == ['unique.mov']
            manifest = json.loads(archive.read('manifest.json'))
            assert [item['resolve_selected_import_required'] for item in manifest['items']] == [True, True, False]
            for item, job in zip(manifest['items'], jobs):
                name = next(name for name in item['files'] if name.endswith('Resolve metadata.csv'))
                row, = rows(archive.read(name))
                assert row['Clip Directory'] == source_directory(job.local_path)
            assert 'Selected Media Pool Clips' in archive.read('Resolve metadata instructions.txt').decode()
    finally:
        path.unlink()
