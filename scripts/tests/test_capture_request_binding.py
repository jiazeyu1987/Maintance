"""Parent selection contracts; server restore/capture E2E is recorded separately."""
from copy import deepcopy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]/'backend/src/main/resources'))
from recovery_control_capture_config import bind_documents


class CaptureRequestBinding(unittest.TestCase):
    def setUp(self):
        self.request = dict(action='INCREMENTAL', sourceConfigRef='source-A', parentChainRef='new-full-B')
        self.repository = dict(sources={'source-A': {'configurationPath':'shared-capture.json'}},
                               parentChains={'stale-A':'old-point'})
        self.capture = dict(sourceConfigRef='source-A', parent={'parentChainRef':'stale-A'},
            source=dict(databaseUuid='database-A', sourceIdentity='source-fingerprint',
                        materialPins=[dict(purpose='mysqlbinlog-exporter', reference='exporter')]))
        self.objects = dict(parentExportIndexPin='stale-index', buckets=['test-bucket'])
        self.parent = dict(reference='new-full-B', sourceConfigRef='source-A', pointPin='point-B',
            point=dict(backupId='new-full-B', generationId='new-full-B', commonRecoveryPoint='position-B'),
            capturePoint=dict(backupId='new-full-B', generationId='new-full-B',
                databaseEnd=dict(databaseUuid='database-A'), sourceIdentity='source-fingerprint',
                commonRecoveryPoint='position-B'),
            material=dict(sourceDatabaseUuid='database-A', recoveryPoint='position-B',
                          database=dict(capturePointPin='capture-B')),
            binding=dict(objectContentIndexPin='index-B'))

    def test_selected_new_full_replaces_all_stale_parent_inputs_without_mutating_source(self):
        before = deepcopy((self.repository,self.capture,self.objects))
        repository,capture,objects = bind_documents(
            self.request,self.repository,self.capture,self.objects,self.parent)
        self.assertEqual(repository['parentChains'], {'new-full-B':'point-B'})
        self.assertEqual(capture['parent'], dict(parentChainRef='new-full-B',
            capturePointPin='capture-B',repositoryPointPin='point-B',objectContentIndexPin='index-B'))
        self.assertEqual(objects['parentExportIndexPin'], 'index-B')
        self.assertEqual(before, (self.repository,self.capture,self.objects))

    def test_new_full_removes_previous_incremental_parent_from_both_data_stores(self):
        request=dict(self.request, action='FULL', parentChainRef=None)
        repository,capture,objects=bind_documents(request,self.repository,self.capture,self.objects,None)
        self.assertIsNone(capture['parent'])
        self.assertEqual(repository['parentChains'], {})
        # The real capture worker indexes this field even for a FULL point.
        self.assertIsNone(objects['parentExportIndexPin'])
        self.assertEqual(objects['buckets'], ['test-bucket'])

    def test_wrong_source_or_selected_parent_is_rejected(self):
        for field,value in [('sourceConfigRef','source-B'),('reference','other-full')]:
            parent=deepcopy(self.parent);parent[field]=value
            with self.assertRaisesRegex(Exception,'CAPTURE_PARENT_SOURCE_MISMATCH'):
                bind_documents(self.request,self.repository,self.capture,self.objects,parent)

    def test_parent_identity_generation_and_database_mismatches_are_rejected(self):
        for mutation in [
            lambda p:p['point'].update(generationId='stale-generation'),
            lambda p:p['capturePoint'].update(sourceIdentity='another-source'),
            lambda p:p['material'].update(sourceDatabaseUuid='another-database'),
            lambda p:p['material'].update(recoveryPoint='wrong-position'),
        ]:
            parent=deepcopy(self.parent);mutation(parent)
            with self.assertRaisesRegex(Exception,'CAPTURE_PARENT_IDENTITY_MISMATCH'):
                bind_documents(self.request,self.repository,self.capture,self.objects,parent)

    def test_missing_exporter_is_an_explicit_prerequisite_failure(self):
        self.capture['source']['materialPins']=[]
        with self.assertRaisesRegex(Exception,'CAPTURE_BINLOG_EXPORTER_REQUIRED'):
            bind_documents(self.request,self.repository,self.capture,self.objects,self.parent)
