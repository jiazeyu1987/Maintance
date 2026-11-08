"""Resolve archived application roles from explicit, immutable version paths.

Resolution proves which program belongs to a point. It does not authorize
running that program or relaxing a target's current image identity.
"""
from copy import deepcopy
import hashlib
import re

from recovery_engine import check_pin, parse, require


def _read_version(reference):
    raw = check_pin(reference)
    require(len(raw) == reference['bytes'] and
            hashlib.sha256(raw).hexdigest() == reference['sha256'],
            'ARCHIVED_VERSION_PIN_CHANGED')
    return parse(raw)


def _selected(document, path):
    """Return no match for a missing path; never coerce a JSON key or index."""
    for key in path:
        if type(document) is dict and type(key) is str and key in document:
            document = document[key]
        elif type(document) is list and type(key) is int and 0 <= key < len(document):
            document = document[key]
        else:
            return False, None
    return True, document


def resolve_archive_images(version_pins, bindings, *, reader=None,
                           mismatch_code='ARCHIVED_IMAGE_BINDING_MISMATCH'):
    """Bind each role to exactly one pinned version document and image ID.

    Bindings contain only ``role`` and ``versionPath``. Callers with an existing
    guarded pin reader may supply it; its errors propagate unchanged. Every pin
    is read even when its document has no selected path. Duplicate matches are
    errors, including two documents that contain the same image ID.
    """
    require(type(version_pins) is list and version_pins, 'ARCHIVED_VERSION_PINS_INVALID')
    require(type(bindings) is list and bindings and all(
        type(binding) is dict and set(binding) == {'role', 'versionPath'} and
        type(binding['role']) is str and binding['role'] and
        type(binding['versionPath']) is list and binding['versionPath'] and all(
            type(key) is str or type(key) is int and key >= 0 for key in binding['versionPath'])
        for binding in bindings), 'ARCHIVED_IMAGE_BINDINGS_INVALID')
    require(len({binding['role'] for binding in bindings}) == len(bindings),
            'ARCHIVED_IMAGE_BINDINGS_INVALID')
    require(reader is None or callable(reader), 'ARCHIVED_VERSION_READER_INVALID')
    require(type(mismatch_code) is str and mismatch_code, 'ARCHIVED_IMAGE_ERROR_CODE_INVALID')
    read = _read_version if reader is None else reader
    documents = [(reference, read(reference)) for reference in version_pins]
    resolved = {}
    for binding in bindings:
        matches = [(reference, image) for reference, document in documents
                   for found, image in [_selected(document, binding['versionPath'])] if found]
        require(len(matches) == 1, mismatch_code)
        reference, image = matches[0]
        require(type(image) is str and re.fullmatch('sha256:[0-9a-f]{64}', image), mismatch_code)
        resolved[binding['role']] = dict(imageId=image, versionPin=deepcopy(reference),
                                        versionPath=list(binding['versionPath']))
    return resolved
