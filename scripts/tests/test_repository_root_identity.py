"""Directory identity diagnostics against real temporary filesystem objects."""
import hashlib
import json
import os
from pathlib import Path
import sys
import time

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'ops/recovery'))
import repository_minimal as repository
from repository_records import RepositoryError, canonical, pin_file


@pytest.fixture
def configured(tmp_path):
    root, operations, staging = [tmp_path / name for name in ('nas', 'operations', 'staging')]
    for path in (root, operations, staging):
        path.mkdir()
    (root / 'archives').mkdir()
    identity = tmp_path / 'identity.json'
    identity.write_bytes(canonical(dict(sourceFingerprint='source', databaseUuid='database')))
    path = tmp_path / 'configuration.json'
    path.write_bytes(canonical(dict(schemaVersion='RepositoryMinimumConfiguration/v1',
        repositoryId='diagnostic', repositoryRoot=str(root), operationRoot=str(operations),
        timeoutMilliseconds=30000, responseTimeoutMilliseconds=1000, maxChainPoints=2,
        maxChainAgeSeconds=3600, captureBinderPath=str(tmp_path / 'unused-binder.py'),
        sources={'source': dict(captureCommand=[sys.executable], configurationPath=str(path),
            stagingRoot=str(staging), sourceIdentityPath=str(identity), toolPaths=[sys.executable])},
        parentChains={}, recoveryPoints={}, readback={}, maximumArchiveBytes=10000, minimumFreeBytes=1)))
    request = dict(schemaVersion='SmallAppBackupUiRequest/v1', operationId='identity-check', action='FULL',
        sourceConfigRef='source', parentChainRef=None, recoveryPointRef=None, targetConfigRef=None)
    config = repository.MinimumConfiguration(str(path), request)
    operation = operations / hashlib.sha256(request['operationId'].encode()).hexdigest()
    operation.mkdir()
    return config, request, operation


def document(path):
    return json.loads(path.read_bytes())


def test_baseline_persists_all_roots_and_unchanged_check_writes_no_failure(configured):
    config, _, operation = configured
    config.record_root_identities(operation, 'worker')
    baseline = document(operation / 'root-identity-worker-baseline.json')
    assert baseline['pid'] == os.getpid()
    assert {row['path']: (row['device'], row['inode'], row['mode']) for row in baseline['roots']} == {
        str(path): value for path, value in config.root_identities.items()}
    config.current()
    assert not (operation / 'root-identity-worker-failure.json').exists()


@pytest.mark.parametrize('name', ['root', 'archives', 'evidence', 'staging'])
def test_replacement_is_rejected_with_before_after_and_call_site(configured, name):
    config, _, operation = configured
    config.record_root_identities(operation, 'worker')
    path = getattr(config, name)
    previous = path.with_name(path.name + '-previous')
    path.rename(previous)
    path.mkdir()
    if name == 'evidence':
        operation = path / operation.name
        (previous / operation.name).rename(operation)
    with pytest.raises(RepositoryError, match='REPOSITORY_MINIMUM_ROOT_IDENTITY_CHANGED'):
        config.current()
    failure = document(operation / 'root-identity-worker-failure.json')
    row = next(row for row in failure['changes'] if row['path'] == str(path))
    assert row['expected']['inode'] != row['observed']['inode']
    assert 'inode' in row['changedFields']
    assert any(frame['function'] == 'test_replacement_is_rejected_with_before_after_and_call_site'
        for frame in failure['callStack'])
    assert all(set(frame) == {'file', 'line', 'function'} for frame in failure['callStack'])
    assert failure['baselinePin'] == pin_file(operation / 'root-identity-worker-baseline.json')
    assert config.root_identities[path] != config.directory_identity(path)


def test_missing_directory_records_observation_error_and_still_fails(configured):
    config, _, operation = configured
    config.record_root_identities(operation, 'readback')
    config.archives.rmdir()
    with pytest.raises(FileNotFoundError):
        config.current()
    failure = document(operation / 'root-identity-readback-failure.json')
    assert failure['failureCode'] == 'REPOSITORY_FILENOTFOUNDERROR'
    assert failure['changes'][0]['observed'] is None
    assert failure['changes'][0]['observationError']['errno'] == 2


@pytest.mark.skipif(sys.platform == 'win32', reason='POSIX directory permission bits required')
def test_permission_change_is_rejected(configured):
    config, _, operation = configured
    config.record_root_identities(operation, 'worker')
    config.archives.chmod(0o711 if config.archives.stat().st_mode & 0o777 != 0o711 else 0o700)
    with pytest.raises(RepositoryError, match='REPOSITORY_MINIMUM_ROOT_IDENTITY_CHANGED'):
        config.current()
    assert document(operation / 'root-identity-worker-failure.json')['changes'][0]['changedFields'] == ['mode']


def test_worker_retains_baseline_pin_even_when_deadline_already_expired(configured):
    config, request, operation = configured
    (operation / 'request.json').write_bytes(canonical(request))
    (operation / 'start.json').write_bytes(canonical(dict(configurationPin=config.pin,
        startedAt='2026-10-21T00:00:00Z', deadlineMonotonic=time.monotonic() - 1, readbackOnly=False)))
    assert repository.worker(str(operation)) == 1
    result = document(operation / 'result.json')
    assert result['state'] == 'FAILED_RETAINED'
    assert result['failureCode'] == 'REPOSITORY_BUDGET_EXPIRED'
    assert result['originalResultPins'] == [pin_file(operation / 'root-identity-worker-baseline.json')]
    assert not list(operation.glob('capture-*'))
