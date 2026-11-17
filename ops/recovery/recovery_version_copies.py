"""Select captured version bytes without depending on source-machine paths."""
import hashlib
from recovery_engine import require


def archived_version_pin(reference, payload_pins):
    # Version documents already inside the archive need no relocation.
    if reference in payload_pins:
        return reference
    name = '/semantic-capture/provided-' + hashlib.sha256(reference['path'].encode('utf-8')).hexdigest() + '.bin'
    matches = [p for p in payload_pins if p['path'].replace('\\', '/').endswith(name)]
    require(len(matches) == 1, 'RESTORE_VERSION_COPY_REQUIRED')
    selected = matches[0]
    require(all(selected[k] == reference[k] for k in ('bytes', 'sha256')),
            'RESTORE_VERSION_COPY_CHANGED')
    return selected


def archived_version_pins(material):
    return [archived_version_pin(p, material['payloadPins']) for p in material['versionPins']]
