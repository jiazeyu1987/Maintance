"""Future backup discovery and immutable selection, without running a restore."""
from copy import deepcopy
from contextlib import contextmanager
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from datetime import datetime, timedelta, timezone

sys.path.insert(0, str(Path(__file__).resolve().parents[2]/'backend/src/main/resources'))
import recovery_control_executor as executor
from recovery_control_restore_catalogue import bind_archive_chain, admit_source_catalogue
from recovery_control_smallapp_native import Native


class ArchiveCatalogue(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.scope = self.write(self.root/'scope.json', {'schemaVersion':'RecoverySourceScope/v1', 'sourceIdentityPin': self.write(
            self.root/'identity.json', {'sourceFingerprint':'source-A','databaseUuid':'uuid-A'})})
        self.source = dict(sourceScopePin=self.scope, archiveRoots=[str(self.root/'archives')],
            archiveCatalogue=dict(schemaVersion='RecoveryArchiveCatalogue/v1', maximumPointFiles=100,
                maximumMetadataBytes=1048576, sourceAdmissionPin={'configuration':'private'}))
        self.request = dict(sourceConfigRef='source-A', recoveryPointRef='backup-new', action='RESTORE')

    def write(self, path, value):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, sort_keys=True, separators=(',',':')), encoding='utf-8')
        path.chmod(0o600)
        return executor.pin(path)

    @contextmanager
    def actual_runtime(self, variant):
        """Pure authenticated files, real imports; never caller-granted flags."""
        root = Path(__file__).resolve().parents[2]
        spec = importlib.util.spec_from_file_location('catalogue_qualification_builder',
            root/'ops/backup_engine/build_variants.py')
        builder = importlib.util.module_from_spec(spec); spec.loader.exec_module(builder)
        baseline, _ = (builder.standard_sources() if variant == 'standard'
            else builder.lightweight_sources())
        payload = builder.safe_fixes(baseline) if variant == 'standard' else baseline
        with tempfile.TemporaryDirectory(dir=self.root) as directory:
            engine = Path(directory)
            for name, raw in payload.items():
                path = engine/name; path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(raw)
            expected = {Path(name).stem:engine/name for name in payload
                if name.endswith('.py') and name.count('/') == 1 and
                name.split('/')[0] in ('common','formal')}
            with patch.dict(sys.modules), patch.object(sys, 'path',
                    [str(engine/name) for name in ('common','formal')]+sys.path):
                for name in expected:sys.modules.pop(name, None)
                runtime = importlib.import_module('recovery_minimal_runtime')
                self.assertIs(runtime.supports_main_target_preservation, variant == 'standard')
                try:
                    yield runtime
                finally:
                    for name, path in expected.items():
                        module = sys.modules.get(name)
                        if module is None:continue
                        self.assertEqual(Path(module.__file__).resolve(), path.resolve())
                        self.assertEqual(path.read_bytes(), payload[path.relative_to(engine).as_posix()])

    def point(self, reference, parents=(), generation='full-first'):
        sidecar = self.root/'archives'/reference/'.repository'
        manifest = self.write(sidecar/'manifest.json', dict(schemaVersion='RepositoryManifest/v1',
            backupId=reference, generationId=generation, sourceIdentityPin=self.source_identity,
            pointType='INCREMENTAL' if parents else 'FULL', parentPointPins=list(parents)))
        terminal = self.write(sidecar/'original-exit.json', dict(state='EXITED', processTerminated=True,
            actualExitCode=0))
        readback = self.write(sidecar/'readback-original.json', dict(schemaVersion='RepositoryMinimumReadback/v1',
            operationId=reference, manifestPin=manifest, sourceScopePin=self.scope))
        close = self.write(sidecar/'archive-close.json', dict(schemaVersion='RepositoryMinimumArchiveClose/v1',
            operationId=reference, archiveReaderClosed=True))
        point = self.write(sidecar/'point.json', dict(schemaVersion='RepositoryPoint/v1',backupId=reference,
            generationId=generation,pointType='INCREMENTAL' if parents else 'FULL',parentPointPins=list(parents),
            manifestPin=manifest,originalExitEvidencePin=terminal,readbackEvidencePin=readback,
            ownerCloseEvidencePin=close, integrityState='COMPLETE'))
        self.write(sidecar/'recovery-repository-binding.json', dict(schemaVersion='RecoveryRepositoryBinding/v1',
            backupId=reference,generationId=generation,repositoryPointPin=point,manifestPin=manifest,
            sourceScopePin=self.scope,recoveryMaterialPin={'unused':'owner validates'},objectContentIndexPin={'unused':'owner validates'}))
        return point

    @property
    def source_identity(self):
        return json.loads(Path(self.scope['path']).read_text(encoding='utf-8'))['sourceIdentityPin']

    def test_new_backup_and_complete_parent_prefix_discovered_without_editing_template(self):
        first=self.point('full-first'); second=self.point('increment-second',[first])
        newest=self.point('backup-new',[first,second])
        before=deepcopy(self.source)
        source,binding=bind_archive_chain(self.source,self.request)
        self.assertEqual(self.source,before)
        self.assertEqual(source['recoveryPoints'], {'backup-new':newest})
        self.assertEqual(source['repositoryPointPins'],[first,second,newest])
        self.assertEqual(len(source['repositoryBindingPinsByManifestSha256']),3)
        self.assertEqual(binding['schemaVersion'],'SmallAppArchivePointBinding/v1')
        self.assertEqual(binding['reference'],'backup-new')

    def test_unselected_bad_old_metadata_does_not_replace_requested_point(self):
        self.write(self.root/'archives'/'old-bad'/'.repository'/'point.json', {'broken':True})
        selected=self.point('backup-new')
        source,_=bind_archive_chain(self.source,self.request)
        self.assertEqual(source['recoveryPoints']['backup-new'],selected)

    def test_duplicate_backup_id_is_rejected(self):
        original=self.point('backup-new')
        value=json.loads(Path(original['path']).read_text(encoding='utf-8'))
        self.write(self.root/'archives'/'duplicate'/'.repository'/'point.json',value)
        with self.assertRaisesRegex(Exception,'ARCHIVE_POINT_REFERENCE_AMBIGUOUS'):
            bind_archive_chain(self.source,self.request)

    def test_missing_parent_and_incomplete_prefix_are_rejected(self):
        first=self.point('full-first'); second=self.point('increment-second',[first])
        self.point('backup-new',[second])
        with self.assertRaisesRegex(Exception,'ARCHIVE_PARENT_PREFIX_INVALID'):
            bind_archive_chain(self.source,self.request)

    def test_mutated_parent_bytes_are_not_re_pinned_as_new_originals(self):
        parent=self.point('full-first'); self.point('backup-new',[parent])
        Path(parent['path']).write_text('{}',encoding='utf-8')
        with self.assertRaises(Exception):
            bind_archive_chain(self.source,self.request)

    def test_cross_source_and_failed_original_are_rejected(self):
        selected=self.point('backup-new')
        path=Path(selected['path']).parent/'original-exit.json'
        self.write(path,dict(state='EXITED',processTerminated=True,actualExitCode=1))
        with self.assertRaises(Exception):
            bind_archive_chain(self.source,self.request)

    def test_source_scope_must_match_registered_source(self):
        self.point('backup-new')
        self.source['sourceScopePin']=self.write(self.root/'other-scope.json',{'sourceIdentityPin':self.source_identity})
        with self.assertRaisesRegex(Exception,'ARCHIVE_SOURCE_BINDING_INVALID'):
            bind_archive_chain(self.source,self.request)

    def historical_scope(self, *, foreign=False):
        identity = (self.write(self.root/'foreign-identity.json', {'sourceFingerprint':'foreign'})
                    if foreign else self.source_identity)
        return self.write(self.root/'historical-scope.json', dict(schemaVersion='RecoverySourceScope/v1',
            sourceIdentityPin=identity, endpointHosts=['original-source']))

    def allow_historical_scopes(self, *scopes):
        self.source['archiveCatalogue'].update(schemaVersion='RecoveryArchiveCatalogue/v2',
            sourceScopePins=[self.source['sourceScopePin'], *scopes])

    def test_explicit_historical_scope_keeps_original_complete_chain_and_pins(self):
        current = self.scope
        historical = self.historical_scope()
        self.scope = historical
        first = self.point('full-first')
        second = self.point('backup-new', [first])
        self.scope = current
        self.allow_historical_scopes(historical)
        before = deepcopy(self.source)
        originals = {str(p):p.read_bytes() for p in self.root.rglob('*.json')}
        resolved, binding = bind_archive_chain(self.source,self.request)
        self.assertEqual(resolved['sourceScopePin'], historical)
        self.assertEqual(resolved['repositoryPointPins'], [first,second])
        self.assertNotIn('archiveCatalogue', resolved)
        self.assertEqual(binding['pointPin'], second)
        self.assertEqual(self.source,before)
        self.assertEqual({str(p):p.read_bytes() for p in self.root.rglob('*.json')}, originals)

    def test_historical_scope_is_not_inferred_from_same_identity(self):
        current = self.scope
        historical = self.historical_scope()
        self.scope = historical
        self.point('backup-new')
        self.scope = current
        self.allow_historical_scopes()
        with self.assertRaisesRegex(Exception,'ARCHIVE_SOURCE_BINDING_INVALID'):
            bind_archive_chain(self.source,self.request)

    def test_explicit_scopes_do_not_allow_mixed_scope_parent_chain(self):
        first = self.point('full-first')
        current = self.scope
        historical = self.historical_scope()
        self.scope = historical
        self.point('backup-new', [first])
        self.scope = current
        self.allow_historical_scopes(historical)
        with self.assertRaisesRegex(Exception,'ARCHIVE_CHAIN_SCOPE_MISMATCH'):
            bind_archive_chain(self.source,self.request)

    def test_explicit_scope_cannot_admit_foreign_source_identity(self):
        historical = self.historical_scope(foreign=True)
        self.point('backup-new')
        self.allow_historical_scopes(historical)
        with self.assertRaisesRegex(Exception,'ARCHIVE_SCOPE_IDENTITY_MISMATCH'):
            bind_archive_chain(self.source,self.request)

    def test_explicit_historical_scope_preserves_identity_pin_at_its_original_path(self):
        current = self.scope
        identity = self.write(self.root/'old-source/identity.json',
            json.loads(Path(self.source_identity['path']).read_text(encoding='utf-8')))
        self.assertEqual(identity['sha256'],self.source_identity['sha256'])
        self.assertNotEqual(identity['path'],self.source_identity['path'])
        historical = self.write(self.root/'old-scope.json',dict(schemaVersion='RecoverySourceScope/v1',
            sourceIdentityPin=identity,endpointHosts=['original-source']))
        self.scope = historical
        self.point('backup-new')
        self.scope = current
        self.allow_historical_scopes(historical)
        resolved, _ = bind_archive_chain(self.source,self.request)
        self.assertEqual(resolved['sourceScopePin'],historical)
        point = json.loads(Path(resolved['recoveryPoints']['backup-new']['path']).read_text(encoding='utf-8'))
        manifest = json.loads(Path(point['manifestPin']['path']).read_text(encoding='utf-8'))
        self.assertEqual(manifest['sourceIdentityPin'],identity)

    def test_historical_scope_pin_is_verified_without_repinning(self):
        historical = self.historical_scope()
        self.point('backup-new')
        self.allow_historical_scopes(historical)
        Path(historical['path']).write_text('{}',encoding='utf-8')
        with self.assertRaises(Exception):
            bind_archive_chain(self.source,self.request)

    def test_scope_policy_requires_unique_bounded_list_including_primary_scope(self):
        historical = self.historical_scope()
        self.point('backup-new')
        self.allow_historical_scopes(historical)
        for scopes in ([], [historical], [self.scope,self.scope], [self.scope]*33):
            with self.subTest(scopes=len(scopes)):
                self.source['archiveCatalogue']['sourceScopePins'] = scopes
                with self.assertRaisesRegex(Exception,'ARCHIVE_SOURCE_SCOPES_INVALID'):
                    bind_archive_chain(self.source,self.request)

    def test_v1_catalogue_keeps_exact_fields_and_single_scope_contract(self):
        self.point('backup-new')
        self.source['archiveCatalogue']['sourceScopePins'] = [self.scope]
        with self.assertRaisesRegex(Exception,'ARCHIVE_CATALOGUE_FIELDS_INVALID'):
            bind_archive_chain(self.source,self.request)

    def native_with_archive_catalogue(self, *, restore_only=False):
        root = self.root/'native'
        registration = self.write(root/'registration.json', dict(schemaVersion='ApplicationRegistration/v1',
            applicationId='app-A',sourceConfigRef='source-A',allowedRestoreTargets=[{'configRef':'target-B'}]))
        self.write(root/'registry/applications/app-A.pin.json',registration)
        (root/'registry/points').mkdir()
        archive = self.write(root/'archive-catalogue.json', dict(schemaVersion='SmallAppArchiveRestoreCatalogue/v1',
            sourceConfigRef='source-A',source=self.source,pointPins=[executor.pin(
                self.root/'archives/backup-new/.repository/point.json')]))
        source_owner = self.write(root/'repository.json',{'sources':{'source-A':{}}})
        restore_owner = self.write(root/'recovery.json',dict(sources={'source-A':self.source},targets={'target-B':{}}))
        program = self.write(root/'program.json',{})
        config = dict(taskRoot=str(root), registryRoot=str(root/'registry'),ledgerRoot=str(root/'ledger'),
            engineSelectionRef='safe-engine',programPins={'repository':program,'recovery':program},
            sourceConfigurations={} if restore_only else {'source-A':source_owner},
            restoreConfigurations={'source-A':{'target-B':restore_owner}},
            archiveRestoreCatalogues={'source-A':archive})
        class LocalNative(Native):
            def configuration(inner):return inner.document(inner.config_pin)
        native = LocalNative(self.write(root/'control.json', config))
        return native

    def test_archive_admission_adds_only_recovery_refs_not_incremental_parent_refs(self):
        self.point('backup-new')
        native = self.native_with_archive_catalogue()
        with patch('recovery_control_target_availability.available',return_value=True):
            row = native.selections()['applications'][0]
        self.assertTrue(row['fullReady'])
        self.assertIsNone(row['historyErrorCode'])
        self.assertEqual(row['parentChainRefs'], [])
        self.assertEqual(row['recoveryPointRefs'], ['backup-new'])

    def test_archive_only_source_can_select_restore_without_capture_configuration(self):
        self.point('backup-new')
        native = self.native_with_archive_catalogue(restore_only=True)
        with patch('recovery_control_target_availability.available',return_value=True):
            row = native.selections()['applications'][0]
        self.assertFalse(row['fullReady'])
        self.assertEqual(row['fullErrorCode'], 'SOURCE_RESTORE_ONLY')
        self.assertEqual(row['engineSelectionRef'], 'safe-engine')
        self.assertIsNone(row['historyErrorCode'])
        self.assertEqual(row['parentChainRefs'], [])
        self.assertEqual(row['recoveryPointRefs'], ['backup-new'])
        request = dict(schemaVersion='SmallAppBackupUiRequest/v1',operationId='restore-archive-001',
            action='RESTORE',sourceConfigRef='source-A',parentChainRef=None,
            recoveryPointRef='backup-new',targetConfigRef='target-B')
        with patch('recovery_control_restore_catalogue.for_request',return_value=('resolved-owner','binding')):
            selected = native.resolve(request)
        self.assertEqual(selected['ownerConfigurationPin'], 'resolved-owner')
        for action in ('FULL','INCREMENTAL'):
            request.update(action=action,recoveryPointRef=None,targetConfigRef=None,
                parentChainRef='backup-new' if action=='INCREMENTAL' else None)
            with self.subTest(action=action), self.assertRaisesRegex(Exception,'SOURCE_RESTORE_ONLY'):
                native.resolve(request)

    def test_archive_only_source_reports_blocked_automatic_incremental_plan(self):
        self.point('backup-new')
        native = self.native_with_archive_catalogue(restore_only=True)
        result = native.incremental_plan('source-A')
        self.assertEqual(result['state'],'BLOCKED')
        self.assertEqual(result['reasonCode'],'SOURCE_RESTORE_ONLY')
        self.assertIsNone(result['parentChainRef'])

    def test_explicit_archive_catalogue_cannot_reenable_quarantined_point(self):
        self.point('backup-new')
        native = self.native_with_archive_catalogue()
        self.write(self.root/'native/registry/quarantined-points/backup-new.json',{'preserved':'original marker'})
        with patch('recovery_control_target_availability.available',return_value=True):
            row = native.selections()['applications'][0]
        self.assertEqual(row['historyErrorCode'],'POINT_QUARANTINED')
        self.assertEqual(row['recoveryPointRefs'], [])

    def test_archive_admission_verifies_original_index_point_pin(self):
        self.point('backup-new')
        native = self.native_with_archive_catalogue()
        point = self.root/'archives/backup-new/.repository/point.json'
        value = json.loads(point.read_text(encoding='utf-8'))
        value['unexpected']='tampered after admission'
        self.write(point,value)
        with patch('recovery_control_target_availability.available',return_value=True):
            row = native.selections()['applications'][0]
        self.assertIsNotNone(row['historyErrorCode'])
        self.assertEqual(row['recoveryPointRefs'], [])

    def test_archive_admission_rejects_configuration_for_different_source(self):
        self.point('backup-new')
        native = self.native_with_archive_catalogue()
        config = native.configuration()
        archive = native.document(config['archiveRestoreCatalogues']['source-A'])
        archive['sourceConfigRef']='different-source'
        config['archiveRestoreCatalogues']['source-A']=self.write(self.root/'wrong-source.json',archive)
        native.config_pin = self.write(self.root/'wrong-control.json',config)
        with patch('recovery_control_target_availability.available',return_value=True):
            row = native.selections()['applications'][0]
        self.assertEqual(row['historyErrorCode'],'ARCHIVE_CATALOGUE_SOURCE_MISMATCH')
        self.assertEqual(row['recoveryPointRefs'], [])

    def test_cross_server_native_uses_explicit_catalogue_instead_of_missing_local_point(self):
        owner=dict(sources={'source-A': self.source},targets={'target-B':{}})
        config=dict(sourceConfigurations={'source-A':'source-owner'},
            restoreConfigurations={'source-A':{'target-B':'restore-owner'}},
            programPins={'recovery':'safe-program'})
        registered={'allowedRestoreTargets':[{'configRef':'target-B'}]}
        request=dict(schemaVersion='SmallAppBackupUiRequest/v1',operationId='restore-new-001',
            action='RESTORE',sourceConfigRef='source-A',parentChainRef=None,
            recoveryPointRef='backup-new',targetConfigRef='target-B')
        native=Native.__new__(Native); native.config_pin='native-config'
        with patch.object(native,'configuration',return_value=config), \
                patch.object(native,'registration',return_value=(registered,'registration')), \
                patch.object(native,'document',return_value=owner), \
                patch.object(native,'point',side_effect=AssertionError('copied point required')), \
                patch.object(executor,'verify'), \
                patch('recovery_control_restore_catalogue.for_request',return_value=('resolved-owner','archive-binding')) as bind:
            selected=native.resolve(request)
            self.assertEqual(selected['ownerConfigurationPin'],'resolved-owner')
            self.assertEqual(selected['pointBindingPin'],'archive-binding')
            bind.assert_called_once_with(native,config,request,'restore-owner')

    def test_static_legacy_native_point_validation_is_preserved(self):
        owner=dict(sources={'source-A': {}},targets={'target-B':{}})
        config=dict(sourceConfigurations={'source-A':'source-owner'},
            restoreConfigurations={'source-A':{'target-B':'restore-owner'}},
            programPins={'recovery':'safe-program'})
        request=dict(schemaVersion='SmallAppBackupUiRequest/v1',operationId='restore-old-001',
            action='RESTORE',sourceConfigRef='source-A',parentChainRef=None,
            recoveryPointRef='backup-old',targetConfigRef='target-B')
        native=Native.__new__(Native); native.config_pin='native-config'
        with patch.object(native,'configuration',return_value=config), \
                patch.object(native,'registration',return_value=({'allowedRestoreTargets':[{'configRef':'target-B'}]},'registration')), \
                patch.object(native,'document',return_value=owner), \
                patch.object(native,'point',return_value='original-binding') as point,patch.object(executor,'verify'):
            selected=native.resolve(request)
            self.assertEqual(selected['ownerConfigurationPin'],'restore-owner')
            self.assertEqual(selected['pointBindingPin'],'original-binding')
            point.assert_called_once_with(config,'backup-old','source-A')

    def test_live_source_admission_rejects_quarantine_stale_or_foreign_catalogue(self):
        access=dict(applicationId='app-A',engineSelectionRef='safe-engine')
        payload=dict(observedAt=datetime.now(timezone.utc).isoformat().replace('+00:00','Z'),
            applications=[dict(sourceConfigRef='source-A',applicationId='app-A',
                engineSelectionRef='safe-engine',historyErrorCode=None,recoveryPointRefs=['backup-new'])])
        self.assertEqual(admit_source_catalogue(payload,access,self.request),['backup-new'])
        for mutate in [lambda p:p['applications'][0].update(recoveryPointRefs=[]),
                       lambda p:p['applications'][0].update(engineSelectionRef='fast-engine'),
                       lambda p:p['applications'][0].update(historyErrorCode='POINT_QUARANTINED'),
                       lambda p:p.update(observedAt=(datetime.now(timezone.utc)-timedelta(seconds=61)).isoformat().replace('+00:00','Z'))]:
            invalid=deepcopy(payload);mutate(invalid)
            with self.assertRaises(Exception): admit_source_catalogue(invalid,access,self.request)

    def test_lightweight_control_refuses_main_target_before_configuration_binding(self):
        owner=dict(sources={'source-A': {}}, targets={'target-B':{'mainApplication':{}}})
        config=dict(sourceConfigurations={'source-A':'source-owner'},
            restoreConfigurations={'source-A':{'target-B':'restore-owner'}},programPins={'recovery':'program'})
        request=dict(schemaVersion='SmallAppBackupUiRequest/v1',operationId='main-refusal-001',
            action='RESTORE',sourceConfigRef='source-A',parentChainRef=None,
            recoveryPointRef='backup-old',targetConfigRef='target-B')
        native=Native.__new__(Native);native.config_pin='native-config'
        with self.actual_runtime('lightweight'), \
                patch.object(native,'configuration',return_value=config),patch.object(native,'registration',
                return_value=({'allowedRestoreTargets':[{'configRef':'target-B'}]},'registration')), \
                patch.object(native,'document',return_value=owner),patch.object(native,'point',return_value='binding'), \
                patch.object(executor,'verify'),patch.object(native,'execute') as execute:
            with self.assertRaisesRegex(Exception,'^MAIN_PRESERVATION_REQUIRES_SAFE_ENGINE$'):native.resolve(request)
            execute.assert_not_called()

    def test_main_availability_observes_live_target_and_propagates_identity_errors(self):
        from recovery_control_target_availability import available
        from types import SimpleNamespace
        configuration=dict(targets={'target-B':{'mainApplication':{}}})
        native=SimpleNamespace(document=lambda pin:configuration)
        module=SimpleNamespace(observe_main_target=lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError('MAIN_SERVICE_UNSTABLE')))
        with self.actual_runtime('standard'),patch.dict(sys.modules,{'recovery_main_target':module}), \
                patch('recovery_control_target_availability.unclaimed_target',return_value=True):
            with self.assertRaisesRegex(RuntimeError,'MAIN_SERVICE_UNSTABLE'):
                available(native,'owner','target-B','source-A')

    def test_source_catalogue_can_skip_live_main_probe_without_masking_selected_target_error(self):
        from recovery_control_target_availability import available
        from types import SimpleNamespace
        native=SimpleNamespace(document=lambda pin:dict(targets={'target-B':{'mainApplication':{}}}))
        with self.actual_runtime('standard'), \
                patch('recovery_control_target_availability.unclaimed_target',return_value=True), \
                patch('recovery_main_target.observe_main_target') as observe:
            self.assertTrue(available(native,'owner','target-B','source-A',observe_main=False))
            observe.assert_not_called()


if __name__ == '__main__': unittest.main()
