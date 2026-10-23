"""Focused local protocol/file tests; these are not a Linux restore rehearsal."""
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from recovery_engine import RecoveryError, canonical, load, pin, write
from recovery_data_files import apply_tree, inventory, tree_delta
from recovery_minimal import run, run_child, validate_result
from recovery_minimal_plan import configuration_contract, request_contract, selected_chain, target_configuration


class MinimalTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name).resolve()
        self.source = self.root/'source'; self.source.mkdir()
        self.archive = self.root/'archive'; self.archive.mkdir()
        self.operations = self.root/'operations'
        self.request = dict(schemaVersion='SmallAppBackupUiRequest/v1', operationId='local-unit-operation',
            action='RESTORE', sourceConfigRef='unit-source', parentChainRef=None,
            recoveryPointRef='unit-I1', targetConfigRef='unit-target')
        self.source_config = dict(sourcePaths=[str(self.source)], archiveRoots=[str(self.archive)],
            sourceContainerIds=['a'*64], sourceNetworkIds=['b'*64], sourceVolumeNames=['unit-source-volume'])
        self.configuration = dict(schemaVersion='RecoveryMinimalConfiguration/v1', operationsRoot=str(self.operations),
            deadlineMilliseconds=20000, pythonPin=pin(sys.executable), maxChainLength=16,
            sources={'unit-source': self.source_config}, targets={})

    def tearDown(self):
        self.temporary.cleanup()

    def fails(self, code, function, *args, **kwargs):
        with self.assertRaises(RecoveryError) as caught:
            function(*args, **kwargs)
        self.assertEqual(caught.exception.code, code)

    def chain(self, *, gap=False, index_gap=False, generation_gap=False):
        identity = write(self.source/'identity.json', dict(sourceFingerprint='unit-source-identity', databaseUuid='unit-source-uuid'))
        scope = write(self.source/'scope.json', dict(sourceIdentityPin=identity, endpointHosts=['http://source.invalid:9000']))
        version = write(self.source/'version.json', dict(schemaVersion='UnitApplicationVersion/v1', version='unit-1'))
        self.source_config.update(sourceScopePin=scope, repositoryPointPins=[], repositoryBindingPinsByManifestSha256={},
                                  recoveryPoints={}, parentChains={})
        previous_inventory = {}; parent_index = None; parents = []
        for number, kind in enumerate(('FULL', 'INCREMENTAL')):
            root = self.archive/str(number); root.mkdir(); metadata = root/'.repository'; metadata.mkdir()
            def data(name, value):
                path = root/name; path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(value if isinstance(value, bytes) else canonical(value))
                return pin(path)
            content = b'full-byte-material' if number == 0 else b'real-delta-fixture-bytes'
            content_ref = data('payload/file.bin', content)
            filename = 'old.bin' if number == 0 else 'new.bin'
            file_inventory = {filename: dict(kind='file', bytes=len(content), sha256=hashlib.sha256(content).hexdigest())}
            changed, deleted = tree_delta(previous_inventory, file_inventory)
            generation = 'generation-2' if generation_gap and number else 'generation-1'
            end = dict(file='mysql-bin.000001', position=100+100*number, databaseUuid='unit-source-uuid', serverVersion='8.0.unit')
            start = None if not number else dict(end, position=101 if gap else 100)
            capture = data('capture.json', dict(schemaVersion='backup-capture-point/v1', backupId='unit-'+str(number),
                generationId=generation, sourceIdentity='unit-source-identity', commonRecoveryPoint='point-'+str(number),
                pointType=kind, databaseEnd=end, databaseDelta={}, fileInventory=file_inventory,
                fileDelta=dict(changedPaths=changed, deletedPaths=deleted)))
            file_ref = data('file-inventory.json', file_inventory)
            expected = data('expected.json', dict(localUnitFixture=True,
                encoding='mysql8-typed-row-multiset-sha256/v1',
                observationIdentity=dict(databaseUuid='unit-source-uuid')))
            reference = data('references.json', dict(schemaVersion='RecoveryReferenceInventory/v1', complete=True,
                recoveryPoint='point-'+str(number), databaseRows=[], objectReferences=[]))
            derived = data('derived.json', dict(schemaVersion='RecoveryDerivedInventory/v1', complete=True,
                recoveryPoint='point-'+str(number), classes={name: dict(classification='NOT_PRESENT',
                requiredForBusiness=False, payloadPins=[], executorKey=None) for name in ('redis', 'queue')}))
            observation = dict(bucket='unit-bucket', state='NO_MULTIPART_UPLOAD_OBSERVED', httpStatus=200,
                rawSha256='0'*64, rawBytes=1, maxUploads=1, uploadCount=0, isTruncated=False, scope='WHOLE_BUCKET_FROM_START')
            multipart = data('multipart-observations.json', dict(state='MULTIPART_EMPTY_POINT_OBSERVATIONS',
                before=[observation], after=[observation]))
            object_inventory = data('versions.jsonl', b'')
            receipt = data('export-receipt.json', dict(buckets=['unit-bucket'], state='S3_EXPORTED_PENDING_RESTORE_PROOF',
                inventoryBytes=0, inventorySha256=object_inventory['sha256'], versionCount=0, deleteMarkerCount=0,
                totalVersionBytes=0, uniqueContentCount=0, multipartObservationsSha256=multipart['sha256']))
            sql = data('payload/database.sql.gz', gzip.compress(b'-- local fixture only\n'))
            raw = data('payload/raw.sql', b'-- local fixture only\n') if number else None
            payloads = sorted([pin(path) for path in root.rglob('*') if path.is_file()], key=lambda ref: Path(ref['path']).relative_to(root).as_posix())
            tree = {path.relative_to(root).as_posix(): ('directory' if path.is_dir() else
                'file|%d|%s' % (pin(path)['bytes'], pin(path)['sha256']))
                for path in root.rglob('*') if '.repository' not in path.relative_to(root).parts}
            tree_ref = write(metadata/'tree.json', tree)
            common = dict(backupId='unit-'+str(number), generationId=generation, pointType=kind,
                parentPointPins=list(parents), commonRecoveryPoint='point-'+str(number), payloadRefs=payloads)
            manifest_ref = write(metadata/'manifest.json', dict(common, schemaVersion='RepositoryManifest/v1',
                payloadTreePin=tree_ref, sourceIdentityPin=identity, versionPins=[version]))
            point_ref = write(metadata/'point.json', dict(common, schemaVersion='RepositoryPoint/v1', manifestPin=manifest_ref))
            material = dict(schemaVersion='RecoveryMaterial/v1', manifestPin=manifest_ref, pointType=kind,
                recoveryPoint='point-'+str(number), sourceFingerprint='unit-source-identity', sourceDatabaseUuid='unit-source-uuid',
                sourceScopePin=scope, versionPins=[version], payloadPins=payloads, referenceInventoryPin=reference, derivedInventoryPin=derived,
                database=dict(method='FORMAL_SQL_FULL' if not number else 'BINLOG_SQL', startPosition=start,
                    endPosition=end, sqlPin=sql, rawSqlPin=raw, expectedDataPin=expected, capturePointPin=capture),
                objects=dict(method='PHYSICAL_FILES', capturePointPin=capture, fileInventoryPin=file_ref,
                    filePayloadPins={filename: content_ref}, inventoryPin=object_inventory, exportReceiptPin=receipt))
            material_ref = write(metadata/'material.json', material)
            index_ref = write(metadata/'object-index.json', dict(schemaVersion='backup-capture-object-index/v1',
                backupId=common['backupId'], generationId=generation, sourceIdentity='unit-source-identity',
                recoveryPoint=common['commonRecoveryPoint'], pointType=kind,
                parentExportIndexPin=None if index_gap else parent_index, inventoryPin=object_inventory,
                exportReceiptPin=receipt, contentPins={}, changedContentSha256=[], repositoryBound=True, manifestPin=manifest_ref))
            binding_path = metadata/'binding.json'
            binding_path.write_bytes(canonical(dict(schemaVersion='RecoveryRepositoryBinding/v1', backupId=common['backupId'],
                generationId=generation, repositoryPointPin=point_ref, manifestPin=manifest_ref, sourceScopePin=scope,
                recoveryMaterialPin=material_ref, objectContentIndexPin=index_ref)))
            self.source_config['repositoryBindingPinsByManifestSha256'][manifest_ref['sha256']] = pin(binding_path)
            self.source_config['repositoryPointPins'].append(point_ref)
            previous_inventory = file_inventory; parent_index = index_ref; parents.append(point_ref)
        self.source_config['recoveryPoints']['unit-I1'] = parents[-1]
        self.source_config['parentChains']['unit-parent'] = parents[:-1]
        return selected_chain(self.configuration, self.request)

    def test_exact_seven_field_contract(self):
        request_contract(self.request)
        self.fails('MINIMAL_REQUEST_INVALID', request_contract, dict(self.request, grantRef='retired'))

    def test_operation_id_cannot_escape_journal(self):
        self.fails('OPERATION_ID_INVALID', request_contract, dict(self.request, operationId='../other'))

    def test_capture_does_not_require_target_readiness(self):
        configuration_contract(self.configuration)
        request_contract(dict(self.request, action='FULL', targetConfigRef=None, recoveryPointRef=None))

    def test_real_file_hash_chain_without_signatures_or_completed_receipts(self):
        source, policy, chain = self.chain()
        self.assertEqual([step[1]['pointType'] for step in chain], ['FULL', 'INCREMENTAL'])
        self.assertNotIn('ownerCloseEvidencePin', chain[0][1])

    def test_lightweight_does_not_compare_binlog_continuity(self):
        self.assertEqual(len(self.chain(gap=True)[2]), 2)

    def test_lightweight_does_not_compare_generation(self):
        self.assertEqual(len(self.chain(generation_gap=True)[2]), 2)

    def test_lightweight_does_not_compare_object_ancestry(self):
        self.assertEqual(len(self.chain(index_gap=True)[2]), 2)

    def test_lightweight_does_not_check_archived_payload_size_or_content(self):
        self.chain()
        (self.archive/'0'/'payload'/'file.bin').write_bytes(b'corrupt')
        selected_chain(self.configuration, self.request)

    def test_payload_bytes_are_not_rechecked_when_size_is_unchanged(self):
        self.chain()
        path = self.archive/'0'/'payload'/'file.bin'
        raw = path.read_bytes()
        path.write_bytes(bytes(byte ^ 1 for byte in raw))
        selected_chain(self.configuration, self.request)

    def test_lightweight_follows_selected_point_without_registry_comparison(self):
        self.chain()
        request = dict(self.request, parentChainRef='unit-parent')
        self.source_config['parentChains']['unit-parent'] = []
        self.assertEqual(len(selected_chain(self.configuration, request)[2]), 2)

    def test_missing_target_still_fails_when_configuration_is_used(self):
        with self.assertRaises(KeyError):
            target_configuration(self.configuration, self.request, self.source_config)

    def test_real_file_full_delta_and_deletion(self):
        _, _, chain = self.chain()
        from recovery_data_files import physical_chain_inputs
        target = self.root/'fresh-files'; target.mkdir()
        for index, (_, prior, after, payloads, _, _) in enumerate(physical_chain_inputs(chain)):
            apply_tree(target, prior, after, payloads, full=index == 0, guard=lambda: None)
        self.assertEqual(set(inventory(target, lambda: None)), {'new.bin'})
        self.assertEqual((target/'new.bin').read_bytes(), b'real-delta-fixture-bytes')

    def test_nonempty_file_target_not_overwritten(self):
        from recovery_data_files import physical_chain_inputs
        _, _, chain = self.chain()
        target = self.root/'existing-files'; target.mkdir(); existing = target/'keep'; existing.write_bytes(b'keep')
        _, before, after, payloads, _, _ = physical_chain_inputs(chain)[0]
        with self.assertRaises(RecoveryError):
            apply_tree(target, before, after, payloads, full=True, guard=lambda: None)
        self.assertEqual(existing.read_bytes(), b'keep')

    def invocation(self, request=None):
        request_path = self.root/'request.json'; config_path = self.root/'configuration.json'
        write(request_path, self.request if request is None else request); write(config_path, self.configuration)
        return config_path, request_path, self.root/'output.json'

    def test_capture_is_explicitly_routed_to_w03_and_never_executed_here(self):
        paths = self.invocation(dict(self.request, action='FULL'))
        result = run(*paths)
        self.assertEqual((result['state'], result['failureCode']), ('FAILED_RETAINED', 'CAPTURE_ACTION_REQUIRES_W03_ENTRY'))
        self.assertFalse((self.operations/self.request['operationId']/'child-exit.json').exists())

    def test_same_operation_queries_original_and_does_not_redispatch(self):
        paths = self.invocation(dict(self.request, action='FULL'))
        first = run(*paths); second = run(*paths)
        self.assertEqual(first, second)
        self.assertEqual(len(list(self.operations.iterdir())), 1)

    def test_changed_request_cannot_reuse_operation_id(self):
        paths = self.invocation(dict(self.request, action='FULL')); run(*paths)
        write(paths[1], self.request)
        self.fails('OPERATION_ID_INPUT_CONFLICT', run, *paths)

    def test_interrupted_admission_is_unknown_without_dispatch(self):
        paths = self.invocation(); pending = self.operations/self.request['operationId']; pending.mkdir(parents=True)
        result = run(*paths)
        self.assertEqual(result['state'], 'TERMINAL_UNKNOWN')
        self.assertEqual(list(pending.iterdir()), [])

    def test_real_child_failure_exit_is_retained(self):
        self.chain(); paths = self.invocation()
        result = run(*paths)
        self.assertEqual((result['state'], result['failureCode'], result['actualExitCode']),
                         ('FAILED_RETAINED', 'RESTORE_KEYERROR', 1))
        receipt = load(self.operations/self.request['operationId']/'child-exit.json')
        self.assertEqual(receipt['actualExitCode'], 1)
        self.assertEqual(run(*paths), result)
        # Simulate loss of the parent after it retained the child exit, before
        # publishing its final result. Query consumes those same originals.
        original = pin(self.operations/self.request['operationId']/'child-exit.json')
        (self.operations/self.request['operationId']/'result.json').unlink()
        self.assertEqual(run(*paths), result)
        self.assertEqual(pin(original['path']), original)

    def test_actual_subprocess_success_failure_and_timeout(self):
        for code in (0, 7):
            root = self.root/('child-'+str(code)); root.mkdir()
            receipt, reference = run_child([sys.executable, '-c', 'raise SystemExit(%d)' % code], root, 10)
            self.assertEqual(receipt['actualExitCode'], code)
            self.assertFalse(receipt['timedOut'])
        root = self.root/'child-timeout'; root.mkdir()
        receipt, _ = run_child([sys.executable, '-c', 'import time; time.sleep(5)'], root, 0.1)
        self.assertTrue(receipt['timedOut'])
        self.assertIsNotNone(receipt['actualExitCode'])

    def test_entry_timeout_queries_original_without_new_child(self):
        self.configuration['deadlineMilliseconds'] = 1
        paths = self.invocation()
        result = run(*paths)
        self.assertEqual(result['state'], 'TERMINAL_UNKNOWN')
        self.assertEqual(result['data']['originalOperationId'], self.request['operationId'])
        original = pin(self.operations/self.request['operationId']/'child-exit.json')
        self.assertEqual(run(*paths), result)
        self.assertEqual(pin(original['path']), original)

    def test_lightweight_has_no_operations_directory_isolation_precheck(self):
        self.configuration['operationsRoot'] = str(self.source/'journal')
        paths = self.invocation()
        result = run(*paths)
        self.assertTrue(Path(self.configuration['operationsRoot']).is_dir())
        self.assertNotEqual(result['state'], 'SUCCEEDED')

    def test_child_zero_without_complete_output_is_not_success(self):
        self.fails('WORKER_RESULT_INVALID', validate_result, {}, self.request, 0)

    def test_output_owned_by_other_operation_not_overwritten(self):
        paths = self.invocation(); paths[2].write_bytes(b'{"untouched":true}')
        self.fails('OUTPUT_ALREADY_BELONGS_TO_ANOTHER_OPERATION', run, *paths)
        self.assertEqual(paths[2].read_bytes(), b'{"untouched":true}')


if __name__ == '__main__':
    unittest.main()
