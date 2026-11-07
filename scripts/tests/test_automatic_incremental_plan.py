"""Automatic incremental admission using real pinned metadata and durable dispatches."""
from copy import deepcopy
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
import json
import hashlib
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

RESOURCES = Path(__file__).resolve().parents[2] / 'backend/src/main/resources'
sys.path.insert(0, str(RESOURCES))
sys.path.insert(0, str(RESOURCES.parents[3] / 'ops/recovery'))
sys.path.append(str(RESOURCES.parents[3] / 'ops/backup_engine/formal'))
import recovery_control_executor as executor
from recovery_control_smallapp import Failure, Ledger, canonical, local_read, persist, result
from recovery_control_smallapp_native import Native
from recovery_control_smallapp_http import handler

DATABASE_UUID = '9f7a672a-ce77-11f1-9f3a-0242ac1ca820'


def ui_request(operation, source='source-A', parent=None):
    return dict(schemaVersion='SmallAppBackupUiRequest/v1', operationId=operation,
        action='INCREMENTAL' if parent else 'FULL', sourceConfigRef=source,
        parentChainRef=parent, recoveryPointRef=None, targetConfigRef=None)


class LocalNative(Native):
    """Protocol tests read real metadata files; they do not claim a live MySQL probe."""
    def configuration(self):
        return self.document(self.config_pin)

    def incremental_source_observation(self, capture, *, deadline=None):
        return local_read(Path(self.config_pin['path']).parent / 'source-observation.json')


class MetadataFixture:
    def __init__(self, root):
        self.root = root
        for name in ('registry/points', 'registry/applications', 'ledger'):
            (root / name).mkdir(parents=True)
        self.write('capture.json', dict(sourceConfigRef='source-A', source=dict(
            sourceIdentity='identity-A', databaseUuid=DATABASE_UUID)))
        owner = self.write('repository.json', dict(sources={'source-A': dict(
            configurationPath=str(root / 'capture.json'))}))
        registration = self.write('registration.json', dict(schemaVersion='ApplicationRegistration/v1',
            applicationId='app-A', sourceConfigRef='source-A', allowedRestoreTargets=[]))
        self.write('registry/applications/app-A.pin.json', registration)
        config = dict(registryRoot=str(root / 'registry'), ledgerRoot=str(root / 'ledger'),
            sourceConfigurations={'source-A': owner}, restoreConfigurations={}, programPins={})
        self.native = LocalNative(self.write('configuration.json', config))
        self.write('source-observation.json', dict(position=dict(databaseUuid=DATABASE_UUID,
            serverVersion='8.0.36', file='binlog.000010', position=100000, executedGtidSet=''),
            logs=[dict(file='binlog.000010', bytes=100000)]))
        self.points = {}

    def write(self, relative, value):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        persist(path, value)
        return executor.pin(path)

    def point(self, ref, parents=(), finished='2026-11-07T01:00:00Z', source='source-A',
              uuid=DATABASE_UUID, prefix=None, exit_code=0):
        kind = 'INCREMENTAL' if parents else 'FULL'
        ancestors = [self.points[p]['pointPin'] for p in parents]
        generation = parents[0] if parents else ref
        previous = self.points[parents[-1]] if parents else None
        prefix = ancestors if prefix is None else prefix
        common = 'sha256:' + ('1' if not parents else str(len(parents) + 1)) * 64
        end = dict(databaseUuid=uuid, serverVersion='8.0.36', file='binlog.000010',
            position=100 + len(parents) * 100, executedGtidSet='')
        captured = self.write(ref + '/capture-point.json', dict(schemaVersion='backup-capture-point/v1',
            backupId=ref, generationId=generation, pointType=kind, sourceIdentity='identity-A',
            parentPointPin=None if previous is None else previous['capturePin'],
            parentRepositoryPointPin=None if previous is None else previous['pointPin'],
            databaseEnd=end, databaseDelta=dict(kind='SQL_FULL' if not parents else 'BINLOG_SQL',
                parentPosition=None if previous is None else previous['end']),
            sourceRestored=True, commonRecoveryPoint=common))
        terminal = self.write(ref + '/exit.json', dict(state='EXITED', processTerminated=True,
            actualExitCode=exit_code))
        manifest = self.write(ref + '/manifest.json', dict(schemaVersion='RepositoryManifest/v1',
            backupId=ref, generationId=generation, pointType=kind, parentPointPins=prefix,
            commonRecoveryPoint=common))
        point = self.write(ref + '/point.json', dict(schemaVersion='RepositoryPoint/v1', backupId=ref,
            generationId=generation, pointType=kind, parentPointPins=prefix, manifestPin=manifest,
            originalExitEvidencePin=terminal, integrityState='COMPLETE',
            blockedReason='REPOSITORY_RECOVERY_NOT_RUN', commonRecoveryPoint=common))
        material = self.write(ref + '/material.json', dict(schemaVersion='RecoveryMaterial/v1',
            pointType=kind, manifestPin=manifest, recoveryPoint=common, sourceDatabaseUuid=uuid,
            database=dict(capturePointPin=captured)))
        binding = self.write(ref + '/repository-binding.json', dict(schemaVersion='RecoveryRepositoryBinding/v1',
            backupId=ref, generationId=generation, repositoryPointPin=point, manifestPin=manifest,
            recoveryMaterialPin=material))
        output = self.write(ref + '/operation.json', dict(schemaVersion='backup-restore-operation-result/v1',
            operationId=ref, requestId=ref, action=kind, state='SUCCEEDED', actualExitCode=0,
            failureCode=None, originalResultPins=[terminal], startedAt='2026-11-07T00:00:00Z',
            finishedAt=finished, message='Native fixture result', data=dict(pointPin=point, repositoryBindingPin=binding)))
        control = self.write(ref + '/control-binding.json', dict(schemaVersion='SmallAppPointBinding/v2',
            reference=ref, sourceConfigRef=source, resultPin=output))
        self.write('registry/points/' + ref + '.pin.json', control)
        self.points[ref] = dict(pointPin=point, capturePin=captured, end=end, controlPin=control)
        return point

    def enable_epoch(self):
        root = self.root / 'epochs'
        root.mkdir(mode=0o700)
        self.epoch_policy = dict(schemaVersion='SourceBackupEpochPolicy/v1', root=str(root),
            sourceIdentity='identity-A', databaseUuid=DATABASE_UUID, sourceLockPath=str(self.root / 'source.lock'))
        config = self.native.configuration()
        capture = self.write('capture-with-epoch.json', dict(sourceConfigRef='source-A',
            sourceLockPath=self.epoch_policy['sourceLockPath'],
            source=dict(sourceIdentity='identity-A', databaseUuid=DATABASE_UUID)))
        owner = self.write('repository-with-epoch.json', dict(sources={'source-A': dict(configurationPath=capture['path'])}))
        config['sourceConfigurations']['source-A'] = owner
        config['sourceEpochPolicies'] = {'source-A': self.epoch_policy}
        self.native.config_pin = self.write('configuration-with-epoch.json', config)

    def epoch_event(self, previous=None, *, kind='INITIALIZED', state='READY', operation=None):
        policy = self.epoch_policy
        evidence = None
        if kind == 'RESTORE_FINISHED':
            evidence = self.write(operation + '-epoch-exit.json', dict(operationId=operation,
                state='SUCCEEDED' if state == 'READY' else state))
        event = dict(schemaVersion='SourceBackupEpochEvent/v1',
            sequence=0 if previous is None else previous[0]['sequence'] + 1,
            kind=kind, policySha256=hashlib.sha256(canonical(policy)).hexdigest(),
            sourceIdentity=policy['sourceIdentity'], databaseUuid=policy['databaseUuid'],
            sourceLockPath=policy['sourceLockPath'], operationId=operation, state=state,
            previousSha256=None if previous is None else previous[1]['sha256'],
            recordedAt='2026-11-07T00:00:00Z', evidencePin=evidence)
        event['epochId'] = previous[0]['epochId'] if kind == 'RESTORE_FINISHED' else hashlib.sha256(canonical(event)).hexdigest()
        reference = self.write('epochs/%020d.json' % event['sequence'], event)
        return event, reference

    def bind_epoch(self, ref, snapshot=None):
        config = self.native.configuration()
        snapshot = snapshot or self.native.source_epoch(config, 'source-A')
        operation = self.root / 'epoch-publications' / ref
        operation.mkdir(parents=True)
        persist(operation / 'selection.json', {'sourceEpoch': snapshot})
        binding = self.native.document(self.points[ref]['controlPin'])
        self.native.publish_point_epoch(ui_request(ref), operation, binding['resultPin'], config)
        return operation


class AutomaticPlan(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.fixture = MetadataFixture(self.root)
        self.native = self.fixture.native

    def point(self, *args, **kwargs):
        return self.fixture.point(*args, **kwargs)

    def plan(self):
        return self.native.incremental_plan('source-A')

    def test_empty_registry_requires_a_full_baseline(self):
        plan = self.plan()
        self.assertEqual((plan['state'], plan['reasonCode']), ('BASELINE_REQUIRED', 'NO_SUCCESSFUL_FULL_BASELINE'))
        self.assertIsNone(plan['parentChainRef'])

    def test_complete_chain_is_selected_without_spug_history(self):
        self.point('full-root')
        self.point('increment-one', ['full-root'], finished='2026-11-07T01:01:00Z')
        self.point('increment-two', ['full-root', 'increment-one'], finished='2026-11-07T01:02:00Z')
        plan = self.plan()
        self.assertEqual(plan['schemaVersion'], 'AutomaticIncrementalPlan/v1')
        self.assertEqual((plan['state'], plan['parentChainRef'], plan['baseFullRef'], plan['chainDepth']),
            ('READY', 'increment-two', 'full-root', 3))
        self.assertEqual(plan['baseFinishedAt'], '2026-11-07T01:00:00Z')
        self.assertEqual(plan['basePointType'], 'FULL')
        self.assertEqual(plan['parentPointType'], 'INCREMENTAL')
        self.assertEqual(plan, self.plan())
        self.assertNotIn(str(self.root), json.dumps(plan))
        self.assertRegex(plan['planDigest'], r'^[0-9a-f]{64}$')
        self.assertRegex(plan['evidenceDigest'], r'^[0-9a-f]{64}$')
        public_body = {key: value for key, value in plan.items() if key != 'planDigest'}
        self.assertEqual(plan['planDigest'], hashlib.sha256(canonical(public_body)).hexdigest())

    def test_newest_native_full_starts_a_new_generation(self):
        self.point('zzz-old-full')
        self.point('zzz-old-increment', ['zzz-old-full'], finished='2026-11-07T01:05:00Z')
        self.point('aaa-new-full', finished='2026-11-07T01:10:00Z')
        self.point('foreign-full', source='source-B', finished='2026-11-07T01:15:00Z')
        plan = self.plan()
        self.assertEqual((plan['state'], plan['parentChainRef'], plan['generationId']),
            ('READY', 'aaa-new-full', 'aaa-new-full'))

    def test_equal_full_times_do_not_use_reference_name_to_choose(self):
        self.point('full-one')
        self.point('full-two')
        self.assertEqual(self.plan()['reasonCode'], 'AMBIGUOUS_LATEST_FULL')
        self.assertEqual(self.plan()['state'], 'BLOCKED')

    def test_branching_chain_is_blocked(self):
        self.point('full-root')
        self.point('increment-one', ['full-root'], finished='2026-11-07T01:01:00Z')
        self.point('increment-two', ['full-root'], finished='2026-11-07T01:02:00Z')
        self.assertEqual(self.plan()['reasonCode'], 'INCREMENTAL_CHAIN_BRANCHED')

    def test_broken_parent_prefix_does_not_fall_back_to_older_point(self):
        root = self.point('full-root')
        middle = self.point('increment-one', ['full-root'], finished='2026-11-07T01:01:00Z')
        self.point('increment-two', ['full-root', 'increment-one'], prefix=[middle],
            finished='2026-11-07T01:02:00Z')
        self.assertEqual(self.plan()['reasonCode'], 'INCREMENTAL_PARENT_PREFIX_INVALID')
        self.assertEqual(self.plan()['state'], 'BLOCKED')

    def test_mutated_original_is_not_re_pinned(self):
        point = self.point('full-root')
        Path(point['path']).write_bytes(b'{}')
        plan = self.plan()
        self.assertEqual((plan['state'], plan['reasonCode']), ('BLOCKED', 'NATIVE_PIN_CHANGED'))

    def test_each_document_is_read_and_hashed_once(self):
        pin = self.point('full-root')
        with patch.object(executor, 'pinned_read', wraps=executor.pinned_read) as reads:
            self.native.document(pin)
        self.assertEqual(reads.call_count, 1)

    def test_cached_original_changed_during_observation_is_rejected_at_close(self):
        pin = self.point('full-root')
        observe = self.native.incremental_source_observation
        def change_after_read(*args, **kwargs):
            actual = observe(*args, **kwargs)
            Path(pin['path']).write_bytes(b'changed-after-original-read')
            return actual
        with patch.object(self.native, 'incremental_source_observation', side_effect=change_after_read):
            plan = self.plan()
        self.assertEqual((plan['state'], plan['reasonCode']), ('BLOCKED', 'INCREMENTAL_PLAN_INPUT_CHANGED'))

    def test_exhausted_plan_budget_is_blocked_without_selecting_a_full(self):
        import recovery_control_incremental_plan as planning
        with patch.object(planning, 'MAX_SECONDS', 0):
            plan = self.plan()
        self.assertEqual((plan['state'], plan['reasonCode']), ('BLOCKED', 'INCREMENTAL_PLAN_TIMEOUT'))

    def test_retired_incremental_payload_metadata_does_not_block_new_full_generation(self):
        self.point('full-old')
        self.point('increment-old', ['full-old'], finished='2026-11-07T01:01:00Z')
        self.point('full-current', finished='2026-11-07T01:02:00Z')
        Path(self.fixture.points['increment-old']['capturePin']['path']).write_bytes(b'changed-old-metadata')
        self.assertEqual((self.plan()['state'], self.plan()['parentChainRef']), ('READY', 'full-current'))
        # Old selectors/native-result originals still determine identity and
        # generation ordering. Their corruption must never be ignored.
        (self.root / 'increment-old/operation.json').write_bytes(b'changed-old-result')
        self.assertEqual((self.plan()['state'], self.plan()['reasonCode']), ('BLOCKED', 'NATIVE_PIN_CHANGED'))

    def test_failed_exit_cannot_become_a_parent(self):
        self.point('full-root', exit_code=1)
        self.assertEqual(self.plan()['reasonCode'], 'INCREMENTAL_ORIGINAL_EXIT_INVALID')

    def test_source_identity_change_requires_full_and_never_selects_old_uuid(self):
        self.point('full-root', uuid='old-uuid')
        self.assertEqual((self.plan()['state'], self.plan()['reasonCode']),
            ('BASELINE_REQUIRED', 'SOURCE_BACKUP_IDENTITY_CHANGED'))

    def test_native_rejects_stale_parent_before_configuration_or_worker_creation(self):
        self.point('full-root')
        self.point('increment-one', ['full-root'], finished='2026-11-07T01:01:00Z')
        with self.assertRaisesRegex(Failure, 'INCREMENTAL_BASELINE_CHANGED'):
            self.native.resolve(ui_request('new-increment-001', parent='full-root'))
        self.assertFalse((self.root / 'request-configurations').exists())

    def test_running_operation_is_busy_but_its_own_worker_can_revalidate(self):
        self.point('full-root')
        operation = ui_request('operation-planned', parent='full-root')
        Ledger(self.root / 'ledger', self.native).reserve(operation, {})
        self.assertEqual(self.plan()['reasonCode'], 'SOURCE_OPERATION_IN_PROGRESS')
        own = self.native.incremental_plan('source-A', exclude_operation=operation['operationId'])
        self.assertEqual(own['state'], 'READY')

    def test_epoch_policy_for_another_source_is_rejected_before_reading_its_journal(self):
        config = self.native.configuration()
        config['sourceEpochPolicies'] = {'source-A': dict(sourceIdentity='another-identity',
            databaseUuid='uuid-A', sourceLockPath=str(self.root / 'source.lock'))}
        with self.assertRaisesRegex(Failure, 'SOURCE_EPOCH_POLICY_BINDING_INVALID'):
            self.native.source_epoch(config, 'source-A')

    def test_purged_parent_requires_full_but_malformed_observation_is_blocked(self):
        self.point('full-root')
        observed = local_read(self.root / 'source-observation.json')
        observed['position']['file'] = 'binlog.000011'
        observed['logs'] = [dict(file='binlog.000011', bytes=100000)]
        (self.root / 'source-observation.json').write_bytes(canonical(observed))
        self.assertEqual((self.plan()['state'], self.plan()['reasonCode']),
            ('BASELINE_REQUIRED', 'INCREMENTAL_PARENT_BINLOG_PURGED'))
        observed['logs'][0]['bytes'] = 'unknown'
        (self.root / 'source-observation.json').write_bytes(canonical(observed))
        self.assertEqual(self.plan()['state'], 'BLOCKED')

    def test_missing_middle_log_and_regressed_position_require_full(self):
        self.point('full-root')
        observed = local_read(self.root / 'source-observation.json')
        observed['position']['file'] = 'binlog.000012'
        observed['logs'].append(dict(file='binlog.000012', bytes=100000))
        (self.root / 'source-observation.json').write_bytes(canonical(observed))
        self.assertEqual(self.plan()['reasonCode'], 'INCREMENTAL_BINLOG_CHAIN_GAP')
        observed['position']['file'] = 'binlog.000010'
        observed['position']['position'] = 50
        observed['logs'] = observed['logs'][:1]
        (self.root / 'source-observation.json').write_bytes(canonical(observed))
        self.assertEqual(self.plan()['reasonCode'], 'INCREMENTAL_SOURCE_POSITION_REGRESSED')

    def test_normal_source_progress_does_not_expire_a_ready_plan(self):
        self.point('full-root')
        before = self.plan()
        observed = local_read(self.root / 'source-observation.json')
        observed['position']['file'] = 'binlog.000011'
        observed['position']['position'] = 300
        observed['logs'].append(dict(file='binlog.000011', bytes=300))
        (self.root / 'source-observation.json').write_bytes(canonical(observed))
        after = self.plan()
        self.assertEqual(after['state'], 'READY')
        self.assertEqual(before['planDigest'], after['planDigest'])

    def test_live_uuid_mismatch_and_unreadable_observation_block(self):
        self.point('full-root')
        observed = local_read(self.root / 'source-observation.json')
        observed['position']['databaseUuid'] = '8f7a672a-ce77-11f1-9f3a-0242ac1ca820'
        (self.root / 'source-observation.json').write_bytes(canonical(observed))
        self.assertEqual((self.plan()['state'], self.plan()['reasonCode']),
            ('BLOCKED', 'INCREMENTAL_LIVE_SOURCE_IDENTITY_CHANGED'))
        (self.root / 'source-observation.json').unlink()
        self.assertEqual(self.plan()['state'], 'BLOCKED')


class ProcessWorker:
    """Real local process evidence exercises transport lifetime, not a fake backup result."""
    def resolve(self, value):
        return {'sourceConfigRef': value['sourceConfigRef']}

    def execute(self, value, directory, selection):
        child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(0.35)'])
        persist(directory / 'process.json', {'pid': child.pid})
        code = child.wait(timeout=10)
        persist(directory / 'exit.json', {'actualExitCode': code, 'processTerminated': True})

    def reconcile(self, value, directory, selection):
        path = directory / 'exit.json'
        if not path.exists():
            return None
        terminal = local_read(path)
        return result(value, 'SUCCEEDED' if terminal['actualExitCode'] == 0 else 'FAILED')


class EpochAdmission(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.fixture = MetadataFixture(self.root)
        self.fixture.enable_epoch()
        self.native = self.fixture.native

    def plan(self):
        return self.native.incremental_plan('source-A')

    def test_uninitialized_epoch_is_an_explicit_blocker(self):
        self.assertEqual((self.plan()['state'], self.plan()['reasonCode']),
            ('BLOCKED', 'BACKUP_EPOCH_UNINITIALIZED'))

    def test_epoch_journal_cannot_be_inside_capture_archive_storage(self):
        self.fixture.epoch_event()
        config = self.native.configuration()
        source = self.native.document(config['sourceConfigurations']['source-A'])['sources']['source-A']
        capture = self.native.document(executor.pin(source['configurationPath']))
        capture['archiveRoot'] = self.fixture.epoch_policy['root']
        pin = self.fixture.write('capture-overlap.json', capture)
        owner = self.fixture.write('repository-overlap.json', dict(sources={'source-A': dict(configurationPath=pin['path'])}))
        config['sourceConfigurations']['source-A'] = owner
        with self.assertRaisesRegex(Failure, 'SOURCE_EPOCH_STORAGE_OVERLAP'):
            self.native.source_epoch(config, 'source-A')

    def test_old_point_without_epoch_binding_requires_a_new_full(self):
        self.fixture.epoch_event()
        self.fixture.point('full-root')
        self.assertEqual((self.plan()['state'], self.plan()['reasonCode']),
            ('BASELINE_REQUIRED', 'BACKUP_POINT_EPOCH_REQUIRED'))

    def test_published_point_is_bound_to_the_actual_successful_result(self):
        self.fixture.epoch_event()
        self.fixture.point('full-root')
        self.fixture.bind_epoch('full-root')
        plan = self.plan()
        self.assertEqual((plan['state'], plan['parentChainRef']), ('READY', 'full-root'))
        sidecar = local_read(self.root / 'registry/point-epochs/full-root.json')
        self.assertEqual(sidecar['pointPin'], self.fixture.points['full-root']['pointPin'])
        self.assertEqual(sidecar['resultPin'], self.native.document(self.fixture.points['full-root']['controlPin'])['resultPin'])

    def test_restore_with_unchanged_database_uuid_invalidates_old_chain(self):
        first = self.fixture.epoch_event()
        self.fixture.point('full-root')
        self.fixture.bind_epoch('full-root')
        started = self.fixture.epoch_event(first, kind='RESTORE_STARTED', state='REPLACING', operation='restore-001')
        self.fixture.epoch_event(started, kind='RESTORE_FINISHED', state='READY', operation='restore-001')
        self.assertEqual((self.plan()['state'], self.plan()['reasonCode']),
            ('BASELINE_REQUIRED', 'BACKUP_POINT_EPOCH_CHANGED'))
        self.fixture.point('full-after-restore', finished='2026-11-07T01:05:00Z')
        self.fixture.bind_epoch('full-after-restore')
        self.assertEqual((self.plan()['state'], self.plan()['parentChainRef']), ('READY', 'full-after-restore'))

    def test_replacing_and_failed_epochs_are_blocked(self):
        first = self.fixture.epoch_event()
        started = self.fixture.epoch_event(first, kind='RESTORE_STARTED', state='REPLACING', operation='restore-001')
        self.assertEqual(self.plan()['state'], 'BLOCKED')
        self.assertIn(self.plan()['reasonCode'], ('BACKUP_EPOCH_NOT_READY',
            'BACKUP_EPOCH_LINUX_LOCK_REQUIRED', 'BACKUP_EPOCH_SOURCE_LOCK_UNAVAILABLE'))
        self.fixture.epoch_event(started, kind='RESTORE_FINISHED', state='FAILED_RETAINED', operation='restore-001')
        self.assertEqual((self.plan()['state'], self.plan()['reasonCode']), ('BLOCKED', 'BACKUP_EPOCH_NOT_READY'))

    def test_daily_plan_uses_formal_epoch_reconciliation_and_retains_real_errors(self):
        import recovery_backup_epoch as epoch
        first = self.fixture.epoch_event()
        self.fixture.epoch_event(first, kind='RESTORE_STARTED', state='REPLACING', operation='restore-001')
        with patch.object(epoch, 'try_reconcile_current', wraps=epoch.try_reconcile_current) as reconciled:
            plan = self.plan()
        reconciled.assert_called_once_with(self.fixture.epoch_policy)
        self.assertEqual(plan['state'], 'BLOCKED')
        self.assertIn(plan['reasonCode'], ('BACKUP_EPOCH_LINUX_LOCK_REQUIRED', 'BACKUP_EPOCH_SOURCE_LOCK_UNAVAILABLE'))

    def test_epoch_change_during_capture_prevents_success_publication(self):
        first = self.fixture.epoch_event()
        snapshot = self.native.source_epoch(self.native.configuration(), 'source-A')
        self.fixture.point('full-root')
        started = self.fixture.epoch_event(first, kind='RESTORE_STARTED', state='REPLACING', operation='restore-001')
        self.fixture.epoch_event(started, kind='RESTORE_FINISHED', state='READY', operation='restore-001')
        with self.assertRaisesRegex(Failure, 'BACKUP_EPOCH_CHANGED_DURING_CAPTURE'):
            self.fixture.bind_epoch('full-root', snapshot)
        self.assertFalse((self.root / 'registry/point-epochs/full-root.json').exists())

    def test_historical_point_binding_is_idempotent_after_later_restore(self):
        first = self.fixture.epoch_event()
        self.fixture.point('full-root')
        operation = self.fixture.bind_epoch('full-root')
        sidecar = self.root / 'registry/point-epochs/full-root.json'
        before = sidecar.read_bytes()
        started = self.fixture.epoch_event(first, kind='RESTORE_STARTED', state='REPLACING', operation='restore-001')
        self.fixture.epoch_event(started, kind='RESTORE_FINISHED', state='READY', operation='restore-001')
        binding = self.native.document(self.fixture.points['full-root']['controlPin'])
        self.native.publish_point_epoch(ui_request('full-root'), operation, binding['resultPin'], self.native.configuration())
        self.assertEqual(sidecar.read_bytes(), before)

    def test_sidecar_cannot_claim_a_new_epoch_with_an_old_event(self):
        first = self.fixture.epoch_event()
        self.fixture.point('full-root')
        self.fixture.bind_epoch('full-root')
        started = self.fixture.epoch_event(first, kind='RESTORE_STARTED', state='REPLACING', operation='restore-001')
        self.fixture.epoch_event(started, kind='RESTORE_FINISHED', state='READY', operation='restore-001')
        path = self.root / 'registry/point-epochs/full-root.json'
        sidecar = local_read(path)
        sidecar['epochId'] = self.native.source_epoch(self.native.configuration(), 'source-A')['epochId']
        path.write_bytes(canonical(sidecar))
        self.assertEqual((self.plan()['state'], self.plan()['reasonCode']),
            ('BLOCKED', 'BACKUP_POINT_EPOCH_EVENT_INVALID'))


class DurableAdmission(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.ledger = Ledger(self.root, ProcessWorker())
        self.addCleanup(self.finish)

    def finish(self):
        for thread in threading.enumerate():
            if thread.name.startswith('operation-'):
                thread.join(timeout=10)

    def test_same_source_is_serialized_and_same_id_is_only_queried(self):
        first = ui_request('operation-first')
        self.assertEqual(self.ledger.submit(first)['state'], 'RUNNING')
        second = self.ledger.submit(ui_request('operation-second'))
        self.assertEqual((second['state'], second['errorCode']), ('FAILED', 'SOURCE_OPERATION_IN_PROGRESS'))
        self.assertFalse((self.root / 'operation-second/process.json').exists())
        self.assertIn(self.ledger.submit(first)['state'], ('RUNNING', 'SUCCEEDED'))
        self.finish()
        self.assertEqual(self.ledger.status('operation-first')['state'], 'SUCCEEDED')
        self.assertEqual(self.ledger.submit(ui_request('operation-third'))['state'], 'RUNNING')

    def test_other_source_can_run_independently(self):
        self.ledger.submit(ui_request('operation-first'))
        self.assertEqual(self.ledger.submit(ui_request('operation-other', 'source-B'))['state'], 'RUNNING')

    def test_unclosed_intent_survives_real_process_exit_and_new_ledger(self):
        code = ('import sys; from pathlib import Path; sys.path.insert(0,sys.argv[1]); '
            'from recovery_control_smallapp import Ledger,decode; '
            'Ledger(Path(sys.argv[2]),None).reserve(decode(sys.argv[3].encode()),{})')
        first = ui_request('operation-orphan')
        completed = subprocess.run([sys.executable, '-B', '-c', code, str(RESOURCES), str(self.root),
            canonical(first).decode()], capture_output=True, timeout=10)
        self.assertEqual(completed.returncode, 0, completed.stderr.decode())
        restarted = Ledger(self.root, ProcessWorker())
        second = restarted.submit(ui_request('operation-restarted'))
        self.assertEqual(second['errorCode'], 'SOURCE_OPERATION_IN_PROGRESS')
        self.assertEqual(restarted.submit(first)['state'], 'RUNNING')
        self.assertFalse((self.root / 'operation-restarted/process.json').exists())


class PlanHttp(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.fixture = MetadataFixture(self.root)
        self.fixture.point('full-root')
        self.token = 'Bearer ' + 'unit_test_authorization_not_a_secret_' + 'a' * 20
        credential = self.root / 'credential.json'
        persist(credential, {'headers': {'Authorization': self.token}})
        config = dict(authCredentialRef=dict(path=str(credential), uid=0, gid=0, mode=0o600),
            allowedClientAddresses=['127.0.0.1'])
        ledger = Ledger(self.root / 'ledger', self.fixture.native)
        self.server = ThreadingHTTPServer(('127.0.0.1', 0), handler(ledger, config))
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.close)

    def close(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)

    def get(self, path, authorized=True):
        connection = HTTPConnection('127.0.0.1', self.server.server_port, timeout=5)
        try:
            connection.request('GET', path, headers={'Authorization': self.token} if authorized else {})
            response = connection.getresponse()
            return response.status, json.loads(response.read())
        finally:
            connection.close()

    def test_authenticated_query_and_bad_requests(self):
        status, value = self.get('/incremental-plan?sourceConfigRef=source-A')
        self.assertEqual((status, value['state']), (200, 'READY'))
        status, value = self.get('/incremental-plan?sourceConfigRef=source-A', authorized=False)
        self.assertEqual(value['errorCode'], 'TRANSPORT_AUTHENTICATION_REQUIRED')
        for suffix in ('', '?sourceConfigRef=', '?sourceConfigRef=source-A&sourceConfigRef=source-A',
                       '?sourceConfigRef=source-A&unexpected=x', '?sourceConfigRef=source-A&unexpected'):
            status, value = self.get('/incremental-plan' + suffix)
            self.assertEqual(value['errorCode'], 'INCREMENTAL_PLAN_QUERY_INVALID')


if __name__ == '__main__':
    unittest.main()
