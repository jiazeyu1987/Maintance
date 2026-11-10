"""Private MAIN readback originals; actual local SMB/file protocol only."""
from contextlib import contextmanager
import hashlib
import importlib
import os
from pathlib import Path
import stat

import pytest

from test_recovery_target_preservation import readback_configuration
from recovery_engine import pin
from recovery_program_evidence import _Reader
from repository_records import Deadline, canonical, document

pytestmark = pytest.mark.skipif(not __import__('sys').platform.startswith('linux'),
    reason='actual Linux permissions required')


@contextmanager
def ordinary_umask():
    previous = os.umask(0o022)
    try:
        yield
    finally:
        os.umask(previous)


def archive_material(repository):
    archive = repository/'archive'
    (archive/'semantic-capture').mkdir(parents=True)
    names = ['source-inputs', 'object-content-index', 'references', 'derived', 'objects', 'export']
    values = {}
    for name in names:
        path = archive/'semantic-capture'/(name+'.json')
        path.write_bytes(canonical({'provisionedInputCopies': []} if name == 'source-inputs' else {}))
        values['semantic-capture/'+name+'.json'] = pin(path)
    original = {name: dict(reference, path='/original/'+name) for name, reference in values.items()}
    inputs = dict(archiveFilePins=original,
        capturePointPin=dict(path='/original/capture/point.json', bytes=2, sha256=hashlib.sha256(b'{}').hexdigest()),
        objectContentIndexPin=original['semantic-capture/object-content-index.json'],
        semanticSupplement=dict(zip(('referenceInventoryPin', 'derivedInventoryPin',
            'objectInventoryPin', 'objectExportReceiptPin'),
            [original['semantic-capture/'+name+'.json'] for name in ('references','derived','objects','export')])),
        database=dict(expectedDataPin=dict(path='/original/full-data.json',bytes=2,
            sha256=hashlib.sha256(b'{}').hexdigest())))
    inputs_path = archive/'capture-recovery-inputs.json'
    inputs_path.write_bytes(canonical(inputs))
    values['capture-recovery-inputs.json'] = pin(inputs_path)
    sidecar = archive/'.repository'; sidecar.mkdir()
    for name in ('manifest.json','tree.json'):
        (sidecar/name).write_bytes(b'{}')
    expected = {'semantic-capture':'directory', **{name: 'file|'+str(reference['bytes'])+'|'+reference['sha256']
        for name, reference in values.items()}}
    material = dict(manifestPin=pin(sidecar/'manifest.json'),payloadTreePin=pin(sidecar/'tree.json'),
        payloadRefs=list(values.values()))
    return archive, expected, material


@pytest.mark.parametrize('original', ['retained-raw', 'original-index'])
def test_main_readback_originals_are_private_without_repository_cli_umask(tmp_path, monkeypatch, original):
    repository, _, config = readback_configuration(tmp_path, monkeypatch)
    module = importlib.import_module('repository_native_readback')
    with ordinary_umask(), module.PreservationReadback(config, Deadline(30000)) as readback:
        if original == 'retained-raw':
            payload = repository/'payload.json'; payload.write_bytes(b'{}')
            _, reference = readback.read(str(payload),pin(payload),retain=True)
        else:
            archive, expected, material = archive_material(repository)
            _, reference = readback.verify(str(archive),expected,material)
        # The real historical reader enforces the operation's private root.
        reader = _Reader(lambda:None,[Path(config['recordRoot'])])
        assert reader.read(reference) == document(Path(reference['path']).read_bytes())
        assert stat.S_IMODE(Path(reference['path']).stat().st_mode) == 0o600
        for path in readback.records.iterdir():
            assert stat.S_IMODE(path.stat().st_mode) == 0o600
            assert path.stat().st_nlink == 1


def test_ordinary_smb_readback_keeps_its_existing_creation_contract(tmp_path,monkeypatch):
    repository, _, config = readback_configuration(tmp_path,monkeypatch)
    module = importlib.import_module('repository_native_readback')
    archive, expected, material = archive_material(repository)
    with ordinary_umask(), module.SmbReadback(config,Deadline(30000)) as readback:
        _, reference = readback.verify(str(archive),expected,material)
        assert stat.S_IMODE(Path(reference['path']).stat().st_mode) == 0o644
        assert all(stat.S_IMODE(path.stat().st_mode) == 0o644 for path in readback.records.iterdir())
