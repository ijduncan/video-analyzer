"""Per-import keyword retrieval and honest attribution using the isolated test DB."""
import copy
from dataclasses import asdict, replace

import pytest

from app.services import job_store


@pytest.fixture
def analyzed_project(asset):
    flash = copy.deepcopy(asset.flash_result)
    flash['scenes'][0]['scene_description'] = 'Boating preparations on a foggy morning'
    flash['scenes'][0]['shots'][0].update(
        dominant_colors=['cyan'], location='harbor', actions=['sailing'],
        visible_text=['PORT'], logos=['Anchor icon'], mood='Hopeful',
        evidence=[{'modality': 'visual', 'start_time': '00:00.000', 'end_time': '00:02.000',
                   'description': 'A triangular sail reflects the sunlight'}],
    )
    third = copy.deepcopy(flash['scenes'][0]['shots'][0])
    third.update(shot_number=3, shot_type='MS', start_time='00:08.000', end_time='00:10.000',
                 visual_description='A bicycle passes a bakery', subjects=['bicycle'],
                 tags=['street'], dominant_colors=['orange'], mood='Busy', actions=['cycling'])
    flash['scenes'].append({'scene_number': 2, 'scene_title': 'Town street',
                            'scene_description': 'Cycling past shops at noon',
                            'start_time': '00:08.000', 'end_time': '00:10.000', 'shots': [third]})
    flash.update(total_shots=3, total_scenes=2, total_duration='00:10.000')
    return job_store.update_job(asset.job_id, status='analyzing', flash_result=flash,
        metadata={**asset.metadata, 'campaign': 'Nautical launch', 'collections': ['selects'],
                  'rights_status': 'cleared'},
        summary={'executive_summary': 'A winter campaign about travel',
                 'visual_style': 'Archival documentary'},
        deep_results=[
            {'scene_number': 1, 'visual_analysis': {'color_palette': 'Amber tungsten and charcoal',
                                                   'lighting': 'Soft window light', 'composition': 'Symmetrical'},
             'narrative_context': {'story_beat': 'Preparing to depart'},
             'review_status': 'unreviewed'},
            {'scene_number': 2, 'visual_analysis': {'color_palette': 'Magenta neon'},
             'narrative_context': {'story_beat': 'Arriving in town'}, 'review_status': 'unreviewed'},
        ], shot_annotations={'2': {'tags': ['favorite'], 'notes': 'Use the tight detail', 'review_status': 'reviewed'}})


def test_projects_enumerate_import_ids_independently_of_shared_project_metadata(client, analyzed_project):
    other = replace(analyzed_project, job_id='other-import', filename='Another.mov', status='complete',
                    metadata={**analyzed_project.metadata, 'title': ''}, flash_result=None)
    job_store.create_job(other)
    response = client.get('/api/library/projects')
    assert response.status_code == 200
    data = response.json()
    assert data['total'] == 2
    imports = {item['id']: item for item in data['projects']}
    assert imports['test-asset'] == {'id': 'test-asset', 'title': 'Harbor film',
        'filename': 'Harbor commercial.mov', 'status': 'analyzing', 'shot_count': 3}
    assert imports['other-import']['title'] == 'Another'
    assert imports['other-import']['shot_count'] == 0
    assert 'private-provider' not in response.text


def test_import_scope_is_strict_and_preserves_global_activity(client, analyzed_project):
    other = replace(analyzed_project, job_id='other-import', status='queued')
    job_store.create_job(other)
    assert client.get('/api/library/search/shots?q=sailboat').json()['total'] == 2
    scoped = client.get('/api/library/search/shots', params={'job_id': analyzed_project.job_id, 'q': 'sailboat'})
    assert scoped.status_code == 200
    assert scoped.json()['total'] == 1
    assert {shot['job_id'] for shot in scoped.json()['shots']} == {'test-asset'}
    assert scoped.json()['active_jobs'] == 2
    empty = client.get('/api/library/search/shots', params={'job_id': 'test-asset', 'q': 'absentword', 'offset': 50})
    assert empty.json()['total'] == 0 and empty.json()['active_jobs'] == 2
    for unknown in ('missing-import', ''):
        assert client.get('/api/library/search/shots', params={'job_id': unknown}).status_code == 404


def test_combined_section_color_and_shot_type_matches_only_relevant_section(client, analyzed_project):
    response = client.get('/api/library/search/shots', params={'job_id': 'test-asset', 'q': 'amber CU'})
    assert response.status_code == 200
    assert response.json()['total'] == 1
    shot = response.json()['shots'][0]
    assert shot['shot_number'] == 2
    assert shot['match_sources'] == ['Shot metadata', 'Section analysis']
    assert 'Shot metadata: CU' in shot['match_context']
    assert 'Section analysis: Amber tungsten and charcoal' in shot['match_context']
    assert shot['section_context']['scene_description'] == 'Boating preparations on a foggy morning'
    assert shot['section_analysis']['visual_analysis']['color_palette'] == 'Amber tungsten and charcoal'
    assert 'Magenta' not in str(shot['section_analysis'])
    assert client.get('/api/library/search/shots?q=magenta+CU').json()['total'] == 0
    assert client.get('/api/library/search/shots?q=amber+cycling').json()['total'] == 0


@pytest.mark.parametrize('query,source,expected_shots', [
    ('cyan', 'Shot metadata', [1]),
    ('foggy', 'Section analysis', [1, 2]),
    ('symmetrical', 'Section analysis', [1, 2]),
    ('winter', 'Video summary', [1, 2, 3]),
    ('nautical', 'Project metadata', [1, 2, 3]),
    ('reviewed', 'Shot metadata', [2]),
    ('favorite', 'Shot metadata', [2]),
    ('triangular', 'Shot metadata', [1, 3]),
])
def test_match_sources_explain_each_metadata_scope(client, analyzed_project, query, source, expected_shots):
    result = client.get('/api/library/search/shots', params={'q': query, 'job_id': 'test-asset'}).json()
    assert sorted(shot['shot_number'] for shot in result['shots']) == expected_shots
    assert all(shot['match_sources'] == [source] for shot in result['shots'])
    assert all(shot['match_context'].startswith(source + ': ') for shot in result['shots'])


def test_search_retains_filters_and_complete_shot_details(client, analyzed_project):
    response = client.get('/api/library/search/shots', params={
        'job_id': 'test-asset', 'q': 'amber', 'review_status': 'reviewed', 'tag': 'favorite',
        'project': 'Spring launch', 'rights_status': 'cleared', 'collection': 'selects',
    })
    assert response.status_code == 200 and response.json()['total'] == 1
    shot = response.json()['shots'][0]
    assert shot['notes'] == 'Use the tight detail' and shot['human_tags'] == ['favorite']
    assert shot['shot_type'] == 'CU' and shot['camera_movement'] == 'Handheld'
    assert shot['visual_description'] == 'Hands tighten a rope'
    assert shot['video_summary']['visual_style'] == 'Archival documentary'
    assert shot['project_metadata']['campaign'] == 'Nautical launch'
    assert client.get('/api/library/search/shots?job_id=test-asset&project=Other').json()['total'] == 0
    browsed = client.get('/api/library/search/shots?job_id=test-asset&limit=1&offset=1').json()
    assert browsed['total'] == 3 and len(browsed['shots']) == 1
    assert browsed['shots'][0]['match_sources'] == [] and browsed['shots'][0]['match_context'] == ''


def test_parent_context_never_uses_another_import_or_orphan_section(client, analyzed_project):
    other = replace(analyzed_project, job_id='other-import', summary={'executive_summary': 'Exclusive lunar expedition'},
                    deep_results=[{'scene_number': 1, 'visual_analysis': {'color_palette': 'Ultraviolet'}}])
    job_store.create_job(other)
    job_store.update_job('test-asset', deep_results=analyzed_project.deep_results + [
        {'scene_number': 99, 'visual_analysis': {'color_palette': 'Orphaned indigo'}}])
    for query in ('lunar', 'ultraviolet', 'orphaned'):
        scoped = client.get('/api/library/search/shots', params={'job_id': 'test-asset', 'q': query})
        assert scoped.json()['total'] == 0


def test_search_excludes_secrets_internal_warnings_and_history(client, analyzed_project):
    flash = copy.deepcopy(analyzed_project.flash_result)
    shot = flash['scenes'][0]['shots'][0]
    shot.update(file_uri='providersecrettest', analysis_warnings=['internalwarningtest'],
                 api_key='credentialtest', analysis_history=[{'description': 'archivedtest'}])
    deep = copy.deepcopy(analyzed_project.deep_results)
    deep[0]['visual_analysis']['local_path'] = 'localpathtest'
    deep[0]['analysis_warnings'] = ['deepwarningtest']
    summary = {**analyzed_project.summary, 'raw_usage': {'text': 'rawusagetest'}, 'token': 'tokentest'}
    job_store.update_job('test-asset', flash_result=flash, deep_results=deep, summary=summary,
                        analysis_history=[{'flash_result': {'description': 'historytest'}}])
    response = client.get('/api/library/search/shots?job_id=test-asset')
    for hidden in ('providersecrettest', 'internalwarningtest', 'credentialtest', 'archivedtest',
                   'localpathtest', 'deepwarningtest', 'rawusagetest', 'tokentest', 'historytest'):
        assert hidden not in response.text
        assert client.get('/api/library/search/shots', params={'job_id': 'test-asset', 'q': hidden}).json()['total'] == 0
        assert client.get('/api/library', params={'q': hidden}).json()['total'] == 0
    assert 'file_uri' not in response.text and 'analysis_history' not in response.text


@pytest.mark.parametrize('color,unrelated', [
    ('red', 'An adaptation inspired by armored figures with smeared makeup'),
    ('tan', 'Distant mountains remain stationary'),
    ('rose', 'A prose adaptation'),
    ('lime', 'A sublime performance'),
    ('gold', 'A goldfish swims'),
])
def test_color_queries_do_not_match_inside_unrelated_words(client, asset, color, unrelated):
    job_store.update_job(asset.job_id, summary={'executive_summary': unrelated})
    params = {'job_id': asset.job_id, 'q': color}
    assert client.get('/api/library/search/shots', params=params).json()['total'] == 0
    assert client.get('/api/library', params={'q': color}).json()['total'] == 0


def test_red_search_matches_actual_color_and_hyphenated_compounds(client, asset):
    flash = copy.deepcopy(asset.flash_result)
    flash['scenes'][0]['shots'][0]['visual_description'] = 'A red wall beside a sailboat'
    flash['scenes'][0]['shots'][1]['dominant_colors'] = ['Red-orange']
    job_store.update_job(asset.job_id, flash_result=flash,
        summary={'executive_summary': 'An adaptation inspired by armored figures with smeared makeup'})
    response = client.get('/api/library/search/shots', params={'job_id': asset.job_id, 'q': 'red'})
    assert response.status_code == 200 and response.json()['total'] == 2
    matches = {shot['shot_number']: shot for shot in response.json()['shots']}
    assert matches[1]['match_context'] == 'Shot metadata: A red wall beside a sailboat'
    assert matches[2]['match_context'] == 'Shot metadata: Red-orange'
    assert all(shot['match_sources'] == ['Shot metadata'] for shot in matches.values())
    assert client.get('/api/library/search/shots?job_id=test-asset&q=orange').json()['total'] == 1


def test_custom_analysis_is_attributed_to_its_import_and_searches_asset_cards(client, analyzed_project):
    job_store.update_job('test-asset', custom_result={'findings': [{'description': 'Circular match-cut opportunities'}]})
    other = replace(analyzed_project, job_id='other-import',
                    custom_result={'findings': 'Exclusive kaleidoscope treatment'})
    job_store.create_job(other)

    result = client.get('/api/library/search/shots?q=circular').json()
    assert result['total'] == 3
    assert {shot['job_id'] for shot in result['shots']} == {'test-asset'}
    assert all(shot['match_sources'] == ['Custom analysis'] for shot in result['shots'])
    assert all(shot['match_context'] == 'Custom analysis: Circular match-cut opportunities' for shot in result['shots'])
    combined = client.get('/api/library/search/shots?q=circular+CU').json()['shots']
    assert [shot['shot_number'] for shot in combined] == [2]
    assert combined[0]['match_sources'] == ['Shot metadata', 'Custom analysis']
    assert client.get('/api/library/search/shots?job_id=test-asset&q=kaleidoscope').json()['total'] == 0
    cards = client.get('/api/library?q=circular').json()['assets']
    assert [card['job_id'] for card in cards] == ['test-asset']
    assert cards[0]['match_sources'] == ['Custom analysis']


def test_timed_transcript_matches_only_overlapping_shots_and_preserves_original_cues(client, analyzed_project):
    transcript = [
        {'start_time': '00:00.500', 'end_time': '00:01.500', 'text': 'Welcome aboard'},
        {'start_seconds': 3, 'end_seconds': 3.5, 'text': 'Cast off'},
        {'start': 3.5, 'end': 4, 'text': 'Steady now'},
        {'start_time': '00:03.250', 'end_time': '00:03.750', 'text': 'Crossing boundary'},
        {'start_time': '00:08.000', 'end_time': '00:09.500', 'text': 'Fresh croissants'},
    ]
    job_store.update_job('test-asset', technical={**analyzed_project.technical, 'duration_seconds': 10},
                        transcript=transcript)
    other = replace(analyzed_project, job_id='other-import',
                    transcript=[{'start': 0, 'end': 1, 'text': 'Foreign dialogue'}])
    job_store.create_job(other)

    for query, expected in [('welcome', [1]), ('cast', [1]), ('steady', [2]),
                            ('crossing', [1, 2]), ('croissants', [3]), ('foreign', [])]:
        result = client.get('/api/library/search/shots', params={'job_id': 'test-asset', 'q': query}).json()
        assert sorted(shot['shot_number'] for shot in result['shots']) == expected
        assert all(shot['match_sources'] == ['Transcript'] for shot in result['shots'])
    shots = client.get('/api/library/search/shots?job_id=test-asset').json()['shots']
    by_number = {shot['shot_number']: shot for shot in shots}
    assert by_number[1]['transcript_segments'] == [transcript[0], transcript[1], transcript[3]]
    assert by_number[2]['transcript_segments'] == [transcript[2], transcript[3]]
    assert by_number[3]['transcript_segments'] == [transcript[4]]
    cards = client.get('/api/library?q=croissants').json()['assets']
    assert [card['job_id'] for card in cards] == ['test-asset']
    assert cards[0]['match_sources'] == ['Transcript']


def test_invalid_cues_are_not_searchable_or_attached_to_invalid_shot_intervals(client, analyzed_project):
    invalid_cues = [
        {'start': 0, 'end': 1, 'audio_notes': 'Invalidcue sound description'},
        {'text': 'Invalidcue untimed'},
        {'start': -1, 'end': 1, 'text': 'Invalidcue negative'},
        {'start': 0, 'end': 'NaN', 'text': 'Invalidcue nonfinite'},
        {'start': 0, 'end': 9, 'text': 'Invalidcue past source end'},
        {'start': 1, 'end': 1, 'text': 'Invalidcue empty interval'},
        {'start': 2, 'end': 1, 'text': 'Invalidcue reversed'},
        {'start': False, 'end': 1, 'text': 'Invalidcue boolean'},
        {'start': 0, 'end': 1, 'text': '  ', 'speaker': 'Invalidcue empty words'},
        {'start': 0, 'end': 1, 'text': ['Invalidcue text list']},
        'Invalidcue not a cue object',
    ]
    flash = copy.deepcopy(analyzed_project.flash_result)
    flash['scenes'][0]['shots'][0]['end_time'] = 'invalid'
    job_store.update_job('test-asset', flash_result=flash, transcript=invalid_cues + [
        {'start': 0.5, 'end': 1.5, 'text': 'Validcue spoken words'},
    ])
    result = client.get('/api/library/search/shots?job_id=test-asset').json()
    assert all(shot['transcript_segments'] == [] for shot in result['shots'])
    for query in ('invalidcue', 'validcue'):
        assert client.get('/api/library/search/shots', params={'q': query}).json()['total'] == 0
    assert client.get('/api/library?q=invalidcue').json()['total'] == 0
    # A valid asset-level cue is still retrievable when no valid shot covers it.
    assert client.get('/api/library?q=validcue').json()['total'] == 1


def test_custom_and_transcript_context_are_sanitized_without_changing_stored_analysis(client, analyzed_project):
    job_store.update_job('test-asset', custom_result={
        'notes': 'Public geometry', 'api_key': 'customcredentialtest',
        'details': {'file_uri': 'customprovidertest', 'warnings': ['customwarningtest'],
                    'observation': 'Round reflection'},
    }, transcript=[{
        'start': 0.5, 'end': 1.5, 'text': 'Public speech', 'speaker': 'Speaker one',
        'credentials': {'value': 'transcriptcredentialtest'},
        'analysis_history': [{'text': 'transcripthistorytest'}],
    }])
    before = asdict(job_store.get_job('test-asset'))
    response = client.get('/api/library/search/shots?job_id=test-asset')
    shot = response.json()['shots'][0]
    assert shot['custom_analysis'] == {'notes': 'Public geometry', 'details': {'observation': 'Round reflection'}}
    assert shot['transcript_segments'] == [{'start': 0.5, 'end': 1.5, 'text': 'Public speech', 'speaker': 'Speaker one'}]
    for hidden in ('customcredentialtest', 'customprovidertest', 'customwarningtest',
                   'transcriptcredentialtest', 'transcripthistorytest'):
        assert hidden not in response.text
        assert client.get('/api/library/search/shots', params={'q': hidden}).json()['total'] == 0
        assert client.get('/api/library', params={'q': hidden}).json()['total'] == 0
    assert asdict(job_store.get_job('test-asset')) == before
