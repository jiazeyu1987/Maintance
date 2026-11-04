"""Future backup discovery and immutable selection, without running a restore."""
from copy import deepcopy
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
        self.scope = self.write(self.root/'scope.json', {'sourceIdentityPin': self.write(
            self.root/'identity.json', {'sourceFingerprint':'source-A','databaseUuid':'uuid-A'})})
        self.source = dict(sourceScopePin=self.scope, archiveRoots=[str(self.root/'archives')],
            archiveCatalogue=dict(schemaVersion='RecoveryArchiveCatalogue/v1', maximumPointFiles=100,
                maximumMetadataBytes=1048576, sourceAdmissionPin={'configuration':'private'}))
        self.request = dict(sourceConfigRef='source-A', recoveryPointRef='backup-new', action='RESTORE')

    def write(self, path, value):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, sort_keys=True, separators=(',',':')), encoding='utf-8')
        return executor.pin(path)

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
        from types import SimpleNamespace
        native=Native.__new__(Native);native.config_pin='native-config'
        with patch.object(native,'configuration',return_value=config),patch.object(native,'registration',
                return_value=({'allowedRestoreTargets':[{'configRef':'target-B'}]},'registration')), \
                patch.object(native,'document',return_value=owner),patch.object(native,'point',return_value='binding'), \
                patch.object(executor,'verify'),patch.dict(sys.modules,{'recovery_minimal_runtime':SimpleNamespace(MinimalData=object)}):
            with self.assertRaisesRegex(Exception,'MAIN_RESTORE_REQUIRES_SAFE_ENGINE'):native.resolve(request)

    def test_main_availability_observes_live_target_and_propagates_identity_errors(self):
        from recovery_control_target_availability import available
        from types import SimpleNamespace
        configuration=dict(targets={'target-B':{'mainApplication':{}}})
        native=SimpleNamespace(document=lambda pin:configuration)
        module=SimpleNamespace(observe_main_target=lambda *args: (_ for _ in ()).throw(RuntimeError('MAIN_SERVICE_UNSTABLE')))
        with patch.dict(sys.modules,{'recovery_main_target':module,
                'recovery_minimal_runtime':SimpleNamespace(MinimalData=SimpleNamespace(supports_registered_main_targets=True))}), \
                patch('recovery_control_target_availability.unclaimed_target',return_value=True):
            with self.assertRaisesRegex(RuntimeError,'MAIN_SERVICE_UNSTABLE'):
                available(native,'owner','target-B','source-A')

    def test_source_catalogue_can_skip_live_main_probe_without_masking_selected_target_error(self):
        from recovery_control_target_availability import available
        from types import SimpleNamespace
        native=SimpleNamespace(document=lambda pin:dict(targets={'target-B':{'mainApplication':{}}}))
        with patch('recovery_control_target_availability.unclaimed_target',return_value=True):
            self.assertTrue(available(native,'owner','target-B','source-A',observe_main=False))


if __name__ == '__main__': unittest.main()
