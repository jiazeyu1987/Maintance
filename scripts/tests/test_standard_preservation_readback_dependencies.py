"""STANDARD's actual private reader; native Linux files, finite local SMB.

Run only under the manifest-bound candidate carrier. These nodes exercise the
real package methods and do not add missing symbols to its module namespace.
They are not evidence of a NAS connection or an actual business restoration.
"""
import hashlib
import importlib
import json
import os
from pathlib import Path
import stat

import pytest


def actual_reader():
    assert os.name == 'posix', 'NATIVE_LINUX_PRIVATE_FILE_SEMANTICS_REQUIRED'
    root = Path(os.environ['RECOVERY_TEST_FORMAL_DIRECTORY']).parent
    manifest = json.loads((root/'package.json').read_bytes())
    assert manifest['variant'] == 'standard' and manifest['candidateOnly'] is True
    module = importlib.import_module('repository_native_readback')
    path = root/'common/repository_native_readback.py'
    assert Path(module.__file__).resolve() == path.resolve()
    assert hashlib.sha256(path.read_bytes()).hexdigest() == manifest['files'][
        'common/repository_native_readback.py']
    return module


def assert_private_original(reference, raw):
    path = Path(reference['path'])
    assert path.read_bytes() == raw
    assert reference['bytes'] == len(raw)
    assert reference['sha256'] == hashlib.sha256(raw).hexdigest()
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert path.stat().st_nlink == 1


def test_actual_standard_preservation_constructs_and_retains(tmp_path, monkeypatch):
    module = actual_reader()
    from test_recovery_target_preservation import readback_configuration
    from repository_records import Deadline, canonical, pin_file
    repository, protocol, configuration = readback_configuration(tmp_path, monkeypatch)
    payload = repository/'payload.json'
    payload.write_bytes(b'{"actual":"preserved bytes"}\n')
    expected = pin_file(payload)
    with module.PreservationReadback(configuration, Deadline(30000)) as reader:
        actual, retained = reader.read(str(payload), expected, retain=True)
        assert actual == expected
        assert_private_original(retained, payload.read_bytes())
        value = dict(schemaVersion='RepositoryReadbackOriginals/v1',
                     originalPin=expected, readbackPin=retained)
        index = reader._write_original_records(value)
        assert_private_original(index, canonical(value))
        assert protocol.reads == [payload]
        assert len(protocol.registrations) == 1 and protocol.registrations[0]
    assert protocol.registrations == [{}]


def test_actual_standard_preservation_original_record_dependency(tmp_path, monkeypatch):
    module = actual_reader()
    from test_recovery_target_preservation import readback_configuration
    from repository_records import Deadline, canonical
    _, protocol, configuration = readback_configuration(tmp_path, monkeypatch)
    # A real authenticated base reader gives this isolated method its actual
    # records/deadline owner. It does not pretend to construct the subclass:
    # the other node proves that path. No __new__ or missing-global patching.
    with module.SmbReadback(configuration, Deadline(30000)) as reader:
        value = dict(schemaVersion='RepositoryReadbackOriginals/v1',
                     readbackOriginalPins={}, archivedFilePins={})
        result = module.PreservationReadback._write_original_records(reader, value)
        assert_private_original(result, canonical(value))
        with pytest.raises(FileExistsError):
            module.PreservationReadback._write_original_records(reader, value)
    assert protocol.registrations == [{}]
