"""One-use save-dialog grants; writes never accept a free-form destination."""
import os
import secrets
import threading
import time
from pathlib import Path

_lock = threading.Lock()
_grants = {}
EXTENSIONS = {'.zip', '.xml', '.fcpxml', '.otio', '.edl', '.json', '.csv', '.xmp', '.srt'}


def valid_filename(value):
    if not isinstance(value, str) or not value or len(value) > 220 or any(c in value for c in '/\\:\x00') or Path(value).suffix.lower() not in EXTENSIONS:
        raise ValueError('Invalid export filename.')
    return value


def fingerprint(path):
    if path.is_symlink():
        raise ValueError('Choose a regular export file, not a symbolic link.')
    try:
        stat = path.stat()
        if not path.is_file():
            raise ValueError('Choose an export file, not a folder.')
        return stat.st_size, stat.st_mtime_ns, stat.st_ino
    except FileNotFoundError:
        return None


def grant(path, filename):
    valid_filename(filename)
    path = Path(path)
    if not path.is_absolute() or path.suffix.lower() != Path(filename).suffix.lower():
        raise ValueError('Keep the selected export file extension.')
    existing = fingerprint(path)
    ticket = secrets.token_urlsafe(32)
    with _lock:
        now = time.monotonic()
        for key, value in list(_grants.items()):
            if value[0] < now:
                del _grants[key]
        _grants[ticket] = (now + 900, path, existing)
    return {'ticket': ticket, 'path': str(path), 'cancelled': False}


def consume(ticket, extension):
    with _lock:
        item = _grants.pop(ticket, None)
    if not item or item[0] < time.monotonic():
        raise ValueError('Choose an export location again; the save dialog selection expired.')
    _, path, existing = item
    if path.suffix.lower() != '.' + extension or fingerprint(path) != existing:
        raise ValueError('The selected file changed. Choose its location again before overwriting.')
    return path, existing


def save(path, existing, content):
    temporary = path.with_name('.' + path.name + '.' + secrets.token_hex(8) + '.tmp')
    try:
        with temporary.open('xb') as output:
            output.write(content.encode('utf-8') if isinstance(content, str) else content)
            output.flush()
            os.fsync(output.fileno())
        if fingerprint(path) != existing:
            raise ValueError('The selected file changed; export was not overwritten.')
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)
