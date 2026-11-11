"""Unpolled owner success: real Linux processes, files and control publication.

Only live Docker/MySQL is the existing explicit metadata observation boundary.
No backup, business database or remote service is used by this protocol test.
The I1 selector, epoch sidecar and ledger point binding are never pre-created.
"""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'backend/src/main/resources'), str(Path(__file__).resolve().parent)]
import recovery_control_executor as executor
from recovery_control_smallapp import Ledger, Failure, fingerprint, local_read, persist, result
from test_automatic_incremental_plan import MetadataFixture, LocalNative, ui_request
from test_automatic_incremental_async_closure import LAUNCHER, WORKER, overwrite


def unregistered_material(fixture, reference, parent):
    """Write the repository's protocol originals, never control registry files."""
    old = fixture.points[parent]
    full = local_read(Path(old['pointPin']['path']))
    recovery = 'sha256:' + '2' * 64
    end = dict(old['end'], position=200)
    capture = fixture.write(reference + '/payload/capture-content-point.json', dict(
        schemaVersion='backup-capture-point/v1', backupId=reference, generationId=parent,
        pointType='INCREMENTAL', sourceIdentity='identity-A', parentPointPin=old['capturePin'],
        parentRepositoryPointPin=old['pointPin'], databaseEnd=end,
        databaseDelta=dict(kind='BINLOG_SQL', parentPosition=old['end']),
        sourceRestored=True, commonRecoveryPoint=recovery))
    terminal = fixture.write(reference + '/exit.json', dict(state='EXITED',
        processTerminated=True, actualExitCode=0))
    manifest = fixture.write(reference + '/manifest.json', dict(schemaVersion='RepositoryManifest/v1',
        backupId=reference, generationId=parent, pointType='INCREMENTAL',
        parentPointPins=[old['pointPin']], commonRecoveryPoint=recovery,
        createdAt='2026-11-07T02:00:00Z'))
    point = fixture.write(reference + '/point.json', dict(schemaVersion='RepositoryPoint/v1',
        backupId=reference, generationId=parent, pointType='INCREMENTAL',
        parentPointPins=[old['pointPin']], manifestPin=manifest, originalExitEvidencePin=terminal,
        integrityState='COMPLETE', blockedReason=full['blockedReason'], commonRecoveryPoint=recovery))
    material = fixture.write(reference + '/material.json', dict(schemaVersion='RecoveryMaterial/v1',
        pointType='INCREMENTAL', manifestPin=manifest, recoveryPoint=recovery,
        sourceDatabaseUuid=end['databaseUuid'], database=dict(capturePointPin=capture)))
    binding = fixture.write(reference + '/repository-binding.json', dict(
        schemaVersion='RecoveryRepositoryBinding/v1', backupId=reference, generationId=parent,
        repositoryPointPin=point, manifestPin=manifest, recoveryMaterialPin=material))
    return dict(schemaVersion='backup-restore-operation-result/v1', operationId=reference,
        requestId=reference, action='INCREMENTAL', state='SUCCEEDED', actualExitCode=0,
        failureCode=None, originalResultPins=[terminal], startedAt='2026-11-07T01:10:00Z',
        finishedAt='2026-11-07T02:00:00Z', message='Actual protocol worker terminal, no business backup',
        data=dict(pointPin=point, repositoryBindingPin=binding))


class UnpolledFixture:
    def __init__(self, root):
        self.root = root
        self.metadata = MetadataFixture(root)
        self.metadata.enable_epoch()
        self.metadata.epoch_event()
        self.native = self.metadata.native
        config = self.native.configuration()
        owner = local_read(Path(config['sourceConfigurations']['source-A']['path']))
        owner.update(schemaVersion='RepositoryMinimumConfiguration/v1', operationRoot=str(root / 'owners'))
        (root / 'owners').mkdir(mode=0o700)
        self.owner_pin = self.metadata.write('async-owner.json', owner)
        config['sourceConfigurations']['source-A'] = self.owner_pin
        self.native.config_pin = self.metadata.write('async-control.json', config)
        self.metadata.point('full-root')
        self.metadata.bind_epoch('full-root')
        self.before = self.native.incremental_plan('source-A')
        assert self.before['state'] == 'READY' and self.before['parentChainRef'] == 'full-root', self.before
        self.launcher = root / 'waiting-launcher.py'
        self.launcher.write_text(LAUNCHER, encoding='utf-8')
        self.worker = root / 'actual-worker.py'
        self.worker.write_text(WORKER, encoding='utf-8')
        self.reference = 'unpolled-i1'
        self.value = ui_request(self.reference, parent='full-root')
        self.selection = dict(ownerConfigurationPin=self.owner_pin,
            ownerProgramPin=executor.pin(self.launcher), configurationPin=self.native.config_pin,
            sourceEpoch=self.native.source_epoch(config, 'source-A'))
        self.ledger = Ledger(root / 'ledger', self.native)
        self.ledger.reserve(self.value, self.selection)
        self.directory = root / 'ledger' / self.reference
        self.registration_paths = [root / 'registry/points' / (self.reference + '.pin.json'),
            root / 'registry/point-epochs' / (self.reference + '.json'), self.directory / 'point-binding.json']
        self.owner_root = root / 'owners' / hashlib.sha256(self.reference.encode()).hexdigest()
        self.owner_root.mkdir(mode=0o700)
        persist(self.owner_root / 'request.json', self.value)
        persist(self.owner_root / 'start.json', dict(configurationPin=self.owner_pin,
            requestSha256=fingerprint(self.value), readbackOnly=False,
            startedAt='2026-11-07T01:10:00Z', deadlineMonotonic=time.monotonic() + 60))
        self.final = unregistered_material(self.metadata, self.reference, 'full-root')
        persist(self.owner_root / 'terminal-input.json', self.final)
        self.process = None

    def finish(self):
        assert not any(path.exists() for path in self.registration_paths)
        self.process = subprocess.Popen([sys.executable, '-B', str(self.worker), str(self.owner_root)],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        persist(self.owner_root / 'worker-process.json', dict(operationId=self.reference,
            pid=self.process.pid, startedAt='2026-11-07T01:10:00Z'))
        execute = self.directory / 'execute'
        execute.mkdir(mode=0o700)
        terminal = executor.run_owner(executor.pin(Path(sys.executable).resolve()),
            executor.pin(self.launcher), self.owner_pin, executor.pin(self.directory / 'request.json'),
            execute / 'result.json', environment=dict(os.environ), working_directory=str(self.root),
            deadline_milliseconds=5000)
        assert terminal['actualExitCode'] == 2 and terminal['timedOut'] is False
        persist(self.directory / 'completion.json', dict(operationId=self.reference,
            uiRequestSha256=fingerprint(self.value), selection=self.selection,
            result=result(self.value, 'RUNNING', 'REPOSITORY_QUERY_ORIGINAL_OPERATION'), terminal=terminal))
        (self.owner_root / 'release').touch()
        assert self.process.wait(timeout=5) == 0
        assert self.native.operation_metadata(self.value, executor.pin(self.owner_root / 'result.json')) == self.final
        assert not any(path.exists() for path in self.registration_paths)
        self.completion_pin = executor.pin(self.directory / 'completion.json')
        self.result_pin = executor.pin(self.owner_root / 'result.json')

    def close(self):
        if self.process is not None:
            if self.process.poll() is None:
                self.process.terminate()
            self.process.wait(timeout=5)


@pytest.fixture
def unpolled(tmp_path):
    value = UnpolledFixture(tmp_path)
    try:
        value.finish()
        yield value
    finally:
        value.close()


def test_unpolled_success_is_selected_after_control_restart_without_query(unpolled):
    f = unpolled
    # A fresh object has no in-memory worker or remembered terminal status.
    restarted = LocalNative(f.native.config_pin)
    plan = restarted.incremental_plan('source-A')
    assert (plan['state'], plan['parentChainRef'], plan['baseFullRef'], plan['chainDepth']) == (
        'READY', f.reference, 'full-root', 2), plan
    assert all(path.is_file() for path in f.registration_paths)
    assert plan['planDigest'] != f.before['planDigest']
    assert restarted.incremental_plan('source-A') == plan
    with pytest.raises(Failure, match='INCREMENTAL_BASELINE_CHANGED'):
        restarted.resolve(ui_request('stale-next', parent='full-root'))
    assert executor.pin(f.directory / 'completion.json') == f.completion_pin
    assert executor.pin(f.owner_root / 'result.json') == f.result_pin
    assert not (f.directory / 'queries').exists()
    assert len(list((f.root / 'owners').iterdir())) == 1
