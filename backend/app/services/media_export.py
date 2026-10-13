"""Multiple original media references in an FCP7 project for Premiere/Resolve."""
import copy
import csv
import io
import json
import re
import tempfile
import xml.etree.ElementTree as ET
import zipfile
from fractions import Fraction
from pathlib import Path
from urllib.parse import quote

from app.services.library_export import export_library, iter_shots, job_data, portable_document, segment_times, source_filename
from app.services.editor_metadata import editor_metadata
from app.services.nle_export import _fcpxml_timing, _frames, _frame_timecode, _one_line
from app.services.premiere_xml import export_premiere_xml, source_url


def text(parent, tag, value):
    ET.SubElement(parent, tag).text = str(value)


def full_media(job):
    data = job_data(job)
    _, _, duration, _ = _fcpxml_timing(data)
    # Whole originals, not the detected subclips. Keep analysis as logging/markers.
    data['flash_result'] = {'scenes': [{'scene_number': 1, 'shots': [{
        'shot_number': 1, 'start_time': '0', 'end_time': str(duration),
        'visual_description': '', 'tags': [], 'shot_type': '', 'camera_movement': '',
    }]}]}
    return data


def source_project(job):
    if not source_url(job.local_path):
        raise ValueError('Original media has no absolute file reference. Relink it before exporting.')
    return ET.fromstring(export_premiere_xml(full_media(job)))


def export_checks(jobs, format='premiere_xml', layout='timeline'):
    items = []
    for job in jobs:
        reason = None
        try:
            render_editor_export([job], 'Availability check', format, layout)
        except ValueError as exc:
            reason = str(exc)
        items.append({'id': job.job_id, 'filename': source_filename(job.filename),
                      'title': job.metadata.get('title') or source_filename(job.filename),
                      'available': reason is None, 'reason': reason,
                      'analysis_version': str(job.analysis_config.get('started_at') or ''),
                      'analyzed': bool(job.flash_result),
                      'partial': job.status in ('queued', 'analyzing', 'processing', 'error')})
    reason = None
    if format == 'edl':
        if len(jobs) > 999:
            reason = 'CMX3600 EDL supports up to 999 media items; use FCPXML or OTIO for larger selections.'
        elif all(item['available'] for item in items):
            rates = {_fcpxml_timing(job_data(job))[0] for job in jobs}
            if len(rates) > 1:
                reason = 'A combined EDL needs one source frame rate. Use FCPXML or OTIO for mixed rates.'
    return {'items': items, 'format': format, 'reason': reason, 'available': reason is None and all(item['available'] for item in items)}


def source_values(job):
    data = job_data(job)
    if not source_url(job.local_path):
        raise ValueError('Original media has no absolute file reference. Relink it before exporting.')
    return data, _fcpxml_timing(data)


def original_media_url(path):
    value = str(path).replace('\\', '/')
    if value.startswith('//'):
        return quote('file:' + value, safe='/:')
    return quote('file://' + value if value.startswith('/') else 'file:///' + value, safe='/:')


def aspect_ratio(technical):
    value = technical.get('sample_aspect_ratio')
    if value in (None, '', 'N/A', '0:1'):
        return None  # Unreported: let the editor read the original; do not invent square pixels.
    try:
        ratio = Fraction(str(value).replace(':', '/'))
    except (ValueError, ZeroDivisionError) as exc:
        raise ValueError('FCPXML needs a valid recorded pixel aspect ratio; use Resolve OTIO.') from exc
    if ratio <= 0:
        raise ValueError('FCPXML needs a positive recorded pixel aspect ratio; use Resolve OTIO.')
    return ratio


def observations(data):
    yield from ((f"Clip {shot.get('shot_number')}", shot, shot.get('visual_description', ''))
                for _, shot, _ in iter_shots(data))
    yield from (('Dialogue', cue, cue.get('text', '')) for cue in data.get('transcript') or [])


def metadata_notes(job):
    mapped = editor_metadata(job, include_record=True)
    readable = '\n'.join(f"{field['label']}: {field['value']}" for field in mapped['fields'])
    return mapped, readable


def combined_fcpxml(jobs, title, layout='timeline'):
    root = ET.Element('fcpxml', version='1.10')
    root.append(ET.Comment('Whole original media references. Recorded pixel aspect ratios are preserved.'))
    resources = ET.SubElement(root, 'resources')
    event = ET.SubElement(ET.SubElement(root, 'library'), 'event', name=title)
    spine = None
    timeline_rate = None
    record = 0
    for index, job in enumerate(jobs, 1):
        data, (fps, origin, duration, basis) = source_values(job)
        technical = data['technical']
        width, height = technical.get('width'), technical.get('height')
        if any(type(value) is not int or value <= 0 for value in (width, height)):
            raise ValueError('FCPXML needs known source dimensions; use Resolve OTIO.')
        if technical.get('rotation', 0) not in (None, 0):
            raise ValueError('Rotated sources need an FCPXML orientation mapping; use Resolve OTIO.')
        fmt_id, asset_id = f'f{index}', f'a{index}'
        attributes = {'id': fmt_id, 'frameDuration': f'{fps.denominator}/{fps.numerator}s', 'width': str(width), 'height': str(height)}
        if ratio := aspect_ratio(technical):
            attributes.update(paspH=str(ratio.numerator), paspV=str(ratio.denominator))
        ET.SubElement(resources, 'format', attributes)
        time = lambda frame: f'{frame * fps.denominator}/{fps.numerator}s'
        asset = ET.SubElement(resources, 'asset', id=asset_id, name=source_filename(job.filename), format=fmt_id,
            start=time(origin), duration=time(_frames(duration, fps)), hasVideo='1', hasAudio='1' if technical.get('has_audio') else '0')
        channels = technical.get('audio_channels') or []
        if channels and all(type(channel) is int and channel > 0 for channel in channels):
            asset.set('audioSources', str(len(channels))); asset.set('audioChannels', str(sum(channels)))
        ET.SubElement(asset, 'media-rep', kind='original-media', src=original_media_url(job.local_path))
        mapped, readable = metadata_notes(job)
        metadata = ET.SubElement(asset, 'metadata')
        ET.SubElement(metadata, 'md', key='org.videoanalyzer.sourceTimingBasis', value=basis)
        ET.SubElement(metadata, 'md', key='org.videoanalyzer.analysis', value=json.dumps(mapped['record'], ensure_ascii=False))
        if timeline_rate is None:
            timeline_rate = fps
            if layout == 'timeline':
                sequence = ET.SubElement(ET.SubElement(event, 'project', name=title), 'sequence',
                    format=fmt_id, duration='0s', tcStart='0s', tcFormat='NDF')
                spine = ET.SubElement(sequence, 'spine')
        count = _frames(duration, timeline_rate)
        if count <= 0:
            raise ValueError('A source is shorter than one timeline frame.')
        timeline_time = lambda frame: f'{frame * timeline_rate.denominator}/{timeline_rate.numerator}s'
        # Event clips provide the full media library; timeline clips keep selection order.
        destinations = [event] if spine is None else [event, spine]
        for parent in destinations:
            attrs = {'ref': asset_id, 'name': job.metadata.get('title') or source_filename(job.filename),
                     'format': fmt_id, 'start': time(origin), 'duration': time(_frames(duration, fps)) if parent is event else timeline_time(count)}
            if parent is spine:
                attrs['offset'] = timeline_time(record)
            clip = ET.SubElement(parent, 'asset-clip', attrs)
            ET.SubElement(clip, 'note').text = readable
            for field in mapped['fields']:
                if field['key'] == 'keywords':
                    for tag in field.get('xmp_value') or []:
                        ET.SubElement(clip, 'keyword', start=time(origin), duration=time(_frames(duration, fps)), value=str(tag))
            for name, observation, note in observations(data):
                first, last = segment_times(observation, duration)
                first_frame, last_frame = _frames(first, fps), _frames(last, fps)
                if last_frame > first_frame:
                    ET.SubElement(clip, 'marker', start=time(origin + first_frame), duration=time(1), value=name,
                                  note=f'{note}\nSource range: {first}–{last} seconds')
        record += count
    if spine is not None:
        sequence.set('duration', timeline_time(record))
    ET.indent(root)
    return '<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE fcpxml>\n' + ET.tostring(root, encoding='unicode')


def combined_otio(jobs, title, layout='timeline'):
    if layout != 'timeline':
        raise ValueError('Resolve OTIO exports a timeline; choose FCPXML or legacy FCP7 XML for a media library only.')
    import opentimelineio as otio
    timeline = otio.schema.Timeline(name=title)
    video = otio.schema.Track(name='Original media', kind=otio.schema.TrackKind.Video)
    audio = otio.schema.Track(name='Original audio', kind=otio.schema.TrackKind.Audio)
    timeline.tracks.extend([video, audio])
    any_audio = False
    for job in jobs:
        data, (fps, origin, duration, basis) = source_values(job)
        rate = float(fps)
        span = otio.opentime.TimeRange(otio.opentime.RationalTime(origin, rate), otio.opentime.RationalTime(_frames(duration, fps), rate))
        mapped, readable = metadata_notes(job)
        reference = otio.schema.ExternalReference(target_url=original_media_url(job.local_path), available_range=span)
        reference.metadata['video_analyzer'] = {'technical': portable_document(job)['technical'], 'source_timing_basis': basis}
        clip = otio.schema.Clip(name=job.metadata.get('title') or source_filename(job.filename), media_reference=reference, source_range=span)
        clip.metadata['video_analyzer'] = mapped['record']
        clip.metadata['description'] = readable
        for name, observation, note in observations(data):
            first, last = segment_times(observation, duration)
            first_frame, last_frame = _frames(first, fps), _frames(last, fps)
            if last_frame > first_frame:
                marker = otio.schema.Marker(name=name, marked_range=otio.opentime.TimeRange(
                    otio.opentime.RationalTime(origin + first_frame, rate), otio.opentime.RationalTime(last_frame - first_frame, rate)),
                    color=otio.schema.MarkerColor.BLUE, metadata={'note': note, 'description': note})
                clip.markers.append(marker)
        video.append(clip)
        if data['technical'].get('has_audio'):
            any_audio = True
            audio_clip = copy.deepcopy(clip)
            audio_clip.markers.clear()
            audio.append(audio_clip)
        else:
            audio.append(otio.schema.Gap(source_range=otio.opentime.TimeRange(otio.opentime.RationalTime(0, rate), span.duration)))
    if not any_audio:
        timeline.tracks.remove(audio)
    timeline.global_start_time = otio.opentime.RationalTime(0, float(_fcpxml_timing(job_data(jobs[0]))[0]))
    timeline.metadata['video_analyzer'] = {'whole_originals': True, 'media_count': len(jobs),
        'note': 'Original decoder handles pixel aspect/orientation. OTIO metadata is retained; editor field visibility varies.'}
    return otio.adapters.write_to_string(timeline, adapter_name='otio_json')


def combined_edl(jobs, title, layout='timeline'):
    if layout != 'timeline':
        raise ValueError('EDL exports a video-only timeline; choose XML for a media library only.')
    if len(jobs) > 999:
        raise ValueError('CMX3600 EDL supports up to 999 media items; use FCPXML or OTIO.')
    rate = _fcpxml_timing(job_data(jobs[0]))[0]
    if rate not in {Fraction(24), Fraction(25), Fraction(30), Fraction(24000, 1001), Fraction(30000, 1001)}:
        raise ValueError('CMX3600 EDL supports 24, 25, 30, 23.976 or 29.97 fps non-drop sources.')
    nominal = (rate.numerator + rate.denominator - 1) // rate.denominator
    lines = [f'TITLE: {_one_line(title)}', 'FCM: NON-DROP FRAME', f'* FRAME RATE: {rate}',
        '* VIDEO ONLY. AUDIO AND COMPLETE ANALYSIS ARE IN THE METADATA PACKAGE.', '']
    record = 0
    for index, job in enumerate(jobs, 1):
        data, (fps, origin, duration, basis) = source_values(job)
        if fps != rate:
            raise ValueError('A combined EDL needs one source frame rate. Use FCPXML or OTIO for mixed rates.')
        count = _frames(duration, fps)
        if count <= 0:
            raise ValueError('A source is shorter than one EDL frame.')
        reel = f'VA{index:06d}'
        lines.append(f'{index:03d}  {reel} V     C        {_frame_timecode(origin, nominal)} {_frame_timecode(origin + count, nominal)} '
                     f'{_frame_timecode(record, nominal)} {_frame_timecode(record + count, nominal)}')
        _, readable = metadata_notes(job)
        lines.extend([f'* FROM CLIP NAME: {_one_line(source_filename(job.filename))}', f'* SOURCE FILE: {_one_line(job.local_path)}',
                      f'* SOURCE TIMING BASIS: {basis}', f'* COMMENT: {_one_line(readable)}', ''])
        record += count
    return '\n'.join(lines)


def render_editor_export(jobs, title, format='premiere_xml', layout='timeline'):
    exporters = {'premiere_xml': (combined_project, 'xml', 'application/xml'),
                 'fcpxml': (combined_fcpxml, 'fcpxml', 'application/xml'),
                 'otio': (combined_otio, 'otio', 'application/json'), 'edl': (combined_edl, 'edl', 'text/plain')}
    if format not in exporters:
        raise ValueError('Unsupported editor export format.')
    exporter, extension, mime = exporters[format]
    return exporter(jobs, title, layout), extension, mime


def logging(parent, job):
    mapped = editor_metadata(job, include_record=True)
    fields = {field['key']: field['value'] for field in mapped['fields']}
    description = fields.get('description') or '\n'.join(
        shot.get('visual_description', '') for _, shot, _ in iter_shots(job_data(job)))
    element = ET.SubElement(parent, 'logginginfo')
    text(element, 'description', description)
    if fields.get('scene'):
        text(element, 'scene', fields['scene'])
    if fields.get('shot') or fields.get('take'):
        text(element, 'shottake', ' / '.join(fields[key] for key in ('shot', 'take') if fields.get(key)))
    readable = '\n'.join(f"{field['label']}: {field['value']}" for field in mapped['fields'])
    text(element, 'lognote', readable + '\n\nVideo Analyzer analysis:\n' + json.dumps(mapped['record'], ensure_ascii=False))


def markers(parent, job, fps):
    data = job_data(job)
    duration = data['technical']['duration_seconds']
    observations = [(f"Clip {shot.get('shot_number')}", shot, shot.get('visual_description', ''))
                    for _, shot, _ in iter_shots(data)]
    observations += [('Dialogue', cue, cue.get('text', '')) for cue in data.get('transcript') or []]
    for name, observation, note in observations:
        start, end = segment_times(observation, duration)
        first, last = _frames(start, fps), _frames(end, fps)
        if last <= first:
            continue
        marker = ET.SubElement(parent, 'marker')
        text(marker, 'name', name); text(marker, 'comment', note)
        text(marker, 'in', first); text(marker, 'out', last)


def combined_project(jobs, title, layout='timeline'):
    root = ET.Element('xmeml', version='5')
    root.append(ET.Comment('Original media references only. Full source durations; analysis appears as markers and logging.'))
    project = ET.SubElement(root, 'project')
    text(project, 'name', title)
    children = ET.SubElement(project, 'children')
    bin_element = ET.SubElement(children, 'bin')
    text(bin_element, 'name', 'Analyzed media')
    bin_children = ET.SubElement(bin_element, 'children')
    sequence = None
    timeline_rate = None
    record = 0
    for index, job in enumerate(jobs, 1):
        data = job_data(job)
        fps, _, duration, _ = _fcpxml_timing(data)
        source_seq = source_project(job).find('sequence')
        prefix = f'va-media-{index}'
        for element in source_seq.iter():
            if element.get('id'):
                element.set('id', prefix + '-' + element.get('id'))
            if element.tag == 'linkclipref':
                element.text = prefix + '-' + element.text
        filename = source_filename(job.filename)
        name = job.metadata.get('title') or filename
        master_id = prefix + '-master'
        master = ET.SubElement(bin_children, 'clip', id=master_id)
        text(master, 'name', name); text(master, 'duration', _frames(duration, fps))
        master.append(copy.deepcopy(source_seq.find('rate')))
        text(master, 'masterclipid', master_id); text(master, 'ismasterclip', 'TRUE')
        logging(master, job); markers(master, job, fps)
        master_media = copy.deepcopy(source_seq.find('media'))
        for item in master_media.findall('.//clipitem'):
            item.set('id', item.get('id') + '-master')
            item.find('name').text = name
            for tag in ('start', 'end'):
                item.find(tag).text = '-1'
            for link in item.findall('link'):
                ref = link.find('linkclipref'); ref.text += '-master'
            old_logging = item.find('logginginfo')
            if old_logging is not None:
                item.remove(old_logging)
        master.append(master_media)
        if layout == 'bin':
            continue
        if sequence is None:
            sequence = ET.SubElement(children, 'sequence', id='va-selected-timeline')
            text(sequence, 'name', title)
            text(sequence, 'duration', 0)
            sequence.append(copy.deepcopy(source_seq.find('rate')))
            sequence.append(copy.deepcopy(source_seq.find('timecode')))
            timeline_rate = fps
            media = ET.SubElement(sequence, 'media')
            video = ET.SubElement(media, 'video')
            video.append(copy.deepcopy(source_seq.find('media/video/format')))
            ET.SubElement(video, 'track')
        # Timeline start/end use sequence frames; in/out remain source frames.
        count = _frames(duration, timeline_rate)
        if count <= 0:
            raise ValueError(f'{filename}: source is shorter than a timeline frame')
        source_tracks = [source_seq.find('media/video/track'), *source_seq.findall('media/audio/track')]
        destination_tracks = [sequence.find('media/video/track')]
        if len(source_tracks) > 1:
            audio = sequence.find('media/audio')
            if audio is None:
                audio = ET.SubElement(sequence.find('media'), 'audio')
            while len(audio.findall('track')) < len(source_tracks) - 1:
                ET.SubElement(audio, 'track')
            destination_tracks.extend(audio.findall('track')[:len(source_tracks) - 1])
        clip_indices = [len(track.findall('clipitem')) + 1 for track in destination_tracks]
        for track_index, source_track in enumerate(source_tracks):
            if track_index == 0:
                track = sequence.find('media/video/track')
            else:
                audio = sequence.find('media/audio')
                if audio is None:
                    audio = ET.SubElement(sequence.find('media'), 'audio')
                while len(audio.findall('track')) < track_index:
                    ET.SubElement(audio, 'track')
                track = audio.findall('track')[track_index - 1]
            item = source_track.find('clipitem')
            item.find('name').text = name
            text(item, 'masterclipid', master_id)
            item.find('start').text = str(record); item.find('end').text = str(record + count)
            # Source definitions are carried by the master media in the bin.
            file = item.find('file')
            for child in list(file):
                file.remove(child)
            for linked_index, link in enumerate(item.findall('link')):
                link.find('clipindex').text = str(clip_indices[linked_index])
            old_logging = item.find('logginginfo')
            if old_logging is not None:
                item.remove(old_logging)
            if track_index == 0:
                logging(item, job); markers(item, job, fps)
            track.append(item)
        record += count
    if sequence is not None:
        sequence.find('duration').text = str(record)
    ET.indent(root)
    return '<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE xmeml>\n' + ET.tostring(root, encoding='unicode')


def combined_csv(jobs):
    output = io.StringIO(newline='')
    output.write('\ufeff')
    writer = csv.writer(output)
    for index, job in enumerate(jobs):
        rows = list(csv.reader(io.StringIO(export_library(job, 'csv')[0].lstrip('\ufeff'))))
        writer.writerows(rows if index == 0 else rows[1:])
    return output.getvalue()


def build_download(jobs, title, layout, include_metadata, format='premiere_xml'):
    content, extension, _ = render_editor_export(jobs, title, format, layout)
    temporary = tempfile.NamedTemporaryFile(prefix='video-analyzer-export-', suffix='.zip' if include_metadata else '.' + extension, delete=False)
    path = Path(temporary.name)
    temporary.close()
    try:
        if not include_metadata:
            path.write_text(content, encoding='utf-8')
            return path
        with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as archive:
            archive.writestr('Video Analyzer.' + extension, content)
            archive.writestr('library.json', json.dumps({'schema': 'video-analyzer.collection', 'schema_version': '1.0',
                'assets': [portable_document(job) for job in jobs]}, ensure_ascii=False, indent=2))
            archive.writestr('clips.csv', combined_csv(jobs))
            records = []
            for index, job in enumerate(jobs, 1):
                stem = re.sub(r'[^\w .-]', '_', Path(source_filename(job.filename)).stem)[:100].strip(' .') or 'media'
                folder = f'metadata/{index:04d}_{stem}'
                record = {'id': job.job_id, 'filename': source_filename(job.filename), 'files': [], 'unavailable': {}}
                for sidecar_format in ('xmp', 'srt'):
                    try:
                        result, _, sidecar_extension = export_library(job, sidecar_format)
                    except ValueError as exc:
                        record['unavailable'][sidecar_format] = str(exc)
                        continue
                    name = f'{folder}/{stem}.{sidecar_extension}'
                    archive.writestr(name, result)
                    record['files'].append(name)
                records.append(record)
            archive.writestr('manifest.json', json.dumps({'media_count': len(jobs), 'media_included': False,
                'format': format, 'layout': layout, 'editor_file': 'Video Analyzer.' + extension, 'items': records}, ensure_ascii=False, indent=2))
            archive.writestr('Read me.txt', f'Extract this package and import Video Analyzer.{extension}. Legacy Final Cut Pro 7 XML (.xml): File > Import in Premiere or File > Import > Timeline in Resolve. Final Cut Pro X XML (.fcpxml): File > Import > Timeline in Resolve, or Import XML in Final Cut Pro. OTIO and EDL: File > Import > Timeline in Resolve. OTIO is an open interchange format, not a proprietary DRT/DRP project. EDL is video-only; relink by filenames/source timecodes and retain the metadata files.\n\nWhole originals are referenced, not copied. The optional timeline follows selection order. Relink sources if they have moved or are offline. Each format has its own timing and metadata limitations. FCPXML preserves recorded pixel aspect ratios; OTIO leaves image geometry to the original decoder. XML/OTIO contain analysis/dialogue markers, notes and metadata where supported; editor field visibility varies. library.json and XMP retain complete saved analysis, including fields an editor does not import automatically. Use the integration to sync supported native fields. SRTs retain source-relative times, not combined-timeline times. manifest.json lists absent/invalid subtitle exports. AI timestamps are approximate.\n')
        return path
    except BaseException:
        path.unlink(missing_ok=True)
        raise
