"""Resolve Media Pool metadata CSV, using its native export column names.

XML timeline imports do not populate these fields in Resolve 21. Resolve's
metadata dialog matches filenames, not directories. Ambiguous names therefore
need per-source imports into explicitly selected Media Pool items.
UTF-16 with BOM matches Resolve's own CSV export and retains multiline Unicode.
"""
import csv
import io
import json
import ntpath
import re
from collections import Counter
from pathlib import PurePosixPath

from app.services.editor_metadata import editor_metadata
from app.services.library_export import source_filename

FIELDS = ('Description', 'Keywords', 'Scene', 'Shot', 'Take', 'Camera #', 'Roll Card #',
          'Production Name', 'Director', 'DOP', 'Shot Type', 'Move', 'Location', 'Dialog Notes')


def ambiguous_filenames(jobs):
    counts = Counter(source_filename(job.local_path).casefold() for job in jobs)
    return {name for name, count in counts.items() if count > 1}


def source_directory(path):
    value = str(path)
    if value.startswith(('\\\\', '//')) or re.match(r'^[A-Za-z]:[/\\]', value):
        directory = ntpath.dirname(ntpath.normpath(value))
        return directory.rstrip('\\') if directory.startswith('\\\\') else directory
    return str(PurePosixPath(value).parent)


def export_resolve_metadata(jobs):
    output = io.StringIO(newline='')
    writer = csv.DictWriter(output, fieldnames=('File Name', 'Clip Directory', *FIELDS, 'Comments'))
    writer.writeheader()
    for job in jobs:
        mapped = editor_metadata(job, include_record=True)
        native = {field['resolve']: field['value'] for field in mapped['fields'] if field['resolve'] in FIELDS}
        descriptions = '\n\n'.join(f"{shot.get('start_time', '')}–{shot.get('end_time', '')} · Clip {shot['shot_number']}\n"
                                   + shot.get('visual_description', '') for shot in mapped['record']['shots'])
        readable = '\n\n'.join(field['label'] + '\n' + field['value'] for field in mapped['fields'])
        comments = '[Video Analyzer details]\nClip descriptions\n' + descriptions + '\n\n' + readable
        comments += '\n[/Video Analyzer details]\n\n[Video Analyzer analysis]\n'
        comments += json.dumps(mapped['record'], ensure_ascii=False, separators=(',', ':'))
        comments += '\n[/Video Analyzer analysis]'
        writer.writerow({'File Name': source_filename(job.local_path), 'Clip Directory': source_directory(job.local_path),
                         **native, 'Comments': comments})
    return output.getvalue().encode('utf-16')
