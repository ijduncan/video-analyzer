"""Prepare an explicitly selected editor package for the authenticated native panel."""
import base64
import io
import json
import re
import tempfile
import time
import uuid
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

from app.services.editor_bridge import source_fingerprint
from app.services.premiere_xml import source_url

_prepared = {}
MAX_ARCHIVE = 64 * 1024 * 1024
MAX_DOCUMENT = 12 * 1024 * 1024


def finish_import(identifier):
    entry = _prepared.pop(identifier, None)
    if entry:
        entry[0].unlink(missing_ok=True)


def prepare_import(encoded):
    for identifier, (_, expires) in list(_prepared.items()):
        if expires < time.monotonic():
            finish_import(identifier)
    try:
        data = base64.b64decode(encoded, validate=True)
        if len(data) > MAX_ARCHIVE:
            raise ValueError('Editor package exceeds the 64 MB import limit. Export fewer media.')
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            names = archive.namelist()
            if len(names) != len(set(names)):
                raise ValueError('Editor package contains ambiguous entries.')
            def read(name):
                info = archive.getinfo(name)
                if info.file_size > MAX_DOCUMENT or info.flag_bits & 1:
                    raise ValueError('Editor package document is too large or encrypted.')
                return archive.read(info).decode('utf-8-sig')
            pack = json.loads(read('Resolve handoff.json'))
            xml = read('Video Analyzer.xml')
        if (pack.get('schema') != 'video-analyzer.resolve-handoff' or pack.get('version') != 1
                or pack.get('editor_file') != 'Video Analyzer.xml' or pack.get('layout') not in ('timeline', 'bin')
                or not isinstance(pack.get('assets'), list) or not 1 <= len(pack['assets']) <= 500):
            raise ValueError('Choose a current legacy XML editor package with complete metadata.')
        if re.search(r'<!ENTITY|<!DOCTYPE\s+\w+\s+(?:SYSTEM|PUBLIC)|<!DOCTYPE[^>]*\[', xml, re.I):
            raise ValueError('External or embedded XML declarations are not accepted.')
        root = ET.fromstring(xml)
        if root.tag != 'xmeml':
            raise ValueError('Choose a legacy Final Cut Pro 7 XML editor package.')
        urls, identities = set(), set()
        for asset in pack['assets']:
            path = asset['media_path']
            url = source_url(path)
            metadata = asset['metadata']
            identifier = metadata['record']['asset']['id']
            if (not url or url in urls or not Path(path).is_absolute() or identifier in identities
                    or metadata.get('schema_version') != '1.0' or metadata['record'].get('schema') != 'video-analyzer.library'
                    or not isinstance(metadata.get('fields'), list)
                    or not 0 < float(asset['source_fps']) <= 1000 or not 0 < float(asset['duration_seconds'])):
                raise ValueError('Editor package source identity or metadata is invalid.')
            _, original, _ = source_fingerprint(path)
            stat = original.stat()
            signature = {'size_bytes': stat.st_size, 'mtime_ns': stat.st_mtime_ns}
            if asset.get('source_signature') and signature != asset['source_signature']:
                raise ValueError('An original changed since export. Export its current analysis before importing.')
            urls.add(url); identities.add(identifier)
        if set(node.text for node in root.findall('.//file/pathurl')) != urls:
            raise ValueError('Timeline originals do not match the metadata package.')
    except (KeyError, TypeError, zipfile.BadZipFile, UnicodeError, ET.ParseError, OSError) as exc:
        raise ValueError('Choose a current legacy XML editor package; all original media must be online.') from exc
    handle = tempfile.NamedTemporaryFile(prefix='video-analyzer-resolve-', suffix='.xml', delete=False)
    path = Path(handle.name)
    try:
        handle.write(xml.encode('utf-8')); handle.close()
    except BaseException:
        handle.close(); path.unlink(missing_ok=True); raise
    identifier = str(uuid.uuid4())
    _prepared[identifier] = (path, time.monotonic() + 900)
    return {**pack, 'import_id': identifier, 'timeline_path': str(path)}
