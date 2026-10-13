"""Write merged, backed-up XMP beside linked originals; never touch video bytes."""
import copy
import secrets
import threading
import xml.etree.ElementTree as ET
from pathlib import Path

from app.services.library_export import export_library, NS
from app.services.export_destination import fingerprint, save

_lock = threading.Lock()


def merge_xmp(existing, generated):
    new = ET.fromstring(generated)
    if not existing:
        return ET.tostring(new, encoding='utf-8', xml_declaration=True)
    old = ET.fromstring(existing)
    descriptions = old.findall('./rdf:RDF/rdf:Description', NS)
    target = descriptions[0] if descriptions else None
    incoming = new.find('.//rdf:Description', NS)
    if target is None or incoming is None:
        raise ValueError('Existing sidecar is not supported XMP; it was preserved.')
    for node in incoming:
        if not node.tag.startswith('{urn:video-analyzer:') and not ''.join(node.itertext()).strip():
            continue
        owners = [description for description in descriptions
                  if description.find(node.tag) is not None or node.tag in description.attrib]
        if len(owners) > 1:
            raise ValueError('Existing XMP contains ambiguous duplicate fields; it was preserved.')
        owner = owners[0] if owners else target
        previous = owner.find(node.tag)
        if len(owner.findall(node.tag)) > 1:
            raise ValueError('Existing XMP contains ambiguous duplicate fields; it was preserved.')
        if node.tag in owner.attrib:
            if previous is not None or list(node):
                raise ValueError('Existing XMP field cannot be safely merged; it was preserved.')
            del owner.attrib[node.tag]
        if node.tag == f"{{{NS['xmpDM']}}}Tracks" and previous is not None:
            bag = previous.find('rdf:Bag', NS)
            new_bag = node.find('rdf:Bag', NS)
            if bag is None or new_bag is None:
                raise ValueError('Existing XMP marker tracks cannot be safely merged.')
            for track in list(bag):
                if track.findtext('xmpDM:trackName', namespaces=NS) == 'Video Analyzer shot estimates':
                    bag.remove(track)
            bag.extend(copy.deepcopy(list(new_bag)))
            continue
        if node.tag == f"{{{NS['dc']}}}subject" and previous is not None:
            bag = previous.find('rdf:Bag', NS)
            new_bag = node.find('rdf:Bag', NS)
            if bag is None or new_bag is None:
                raise ValueError('Existing XMP keywords cannot be safely merged.')
            known = {item.text for item in bag}
            bag.extend(copy.deepcopy(item) for item in new_bag if item.text not in known)
            continue
        if previous is not None:
            owner.remove(previous)
        owner.append(copy.deepcopy(node))
    return ET.tostring(old, encoding='utf-8', xml_declaration=True)


def write_sidecars(jobs):
    from app.services.editor_bridge import ensure_original_unchanged
    results = []
    with _lock:
        destinations = {}
        for job in jobs:
            key = str(Path(job.local_path).with_suffix('.xmp')).casefold()
            destinations.setdefault(key, []).append(job)
        for job in jobs:
            result = {'id': job.job_id, 'filename': job.filename, 'written': False}
            try:
                source = Path(job.local_path)
                if not source.is_absolute() or not source.is_file():
                    raise ValueError('Original media is offline or missing; sidecar was not written.')
                sidecar = source.with_suffix('.xmp')
                if len(destinations[str(sidecar).casefold()]) > 1:
                    raise ValueError('Selected sources share a sidecar filename; keep them in separate folders before writing XMP.')
                from app.utils.video_formats import get_mime_type
                if any(other.stem.casefold() == source.stem.casefold()
                       and other.name.casefold() != source.name.casefold()
                       and other.is_file() and get_mime_type(other.name)
                       for other in source.parent.iterdir()):
                    raise ValueError('Another video shares this sidecar filename; keep them in separate folders before writing XMP.')
                ensure_original_unchanged(job)
                before = fingerprint(sidecar)
                if before and before[0] > 16 * 1024 * 1024:
                    raise ValueError('Existing sidecar is too large to merge safely; it was preserved.')
                existing = sidecar.read_bytes() if before else b''
                generated = export_library(job, 'xmp')[0]
                content = merge_xmp(existing, generated)
                backup = None
                if content != existing:
                    if existing:
                        backup = sidecar.with_name(sidecar.name + '.video-analyzer-' + secrets.token_hex(8) + '.bak')
                        with backup.open('xb') as output:
                            output.write(existing)
                    ensure_original_unchanged(job)
                    save(sidecar, before, content)
                result.update(written=True, path=str(sidecar), backup=str(backup) if backup else None)
            except Exception as exc:
                detail = getattr(exc, 'detail', str(exc))
                result['error'] = str(detail)
            results.append(result)
    return results
