import unittest
import tempfile
from pathlib import Path
import prepare_target_native as native

class PolicyTests(unittest.TestCase):
    def test_dynamic_catalogue_owner_inherits_pinned_parent_policy(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            (root/'full/.repository').mkdir(parents=True)
            (root/'incremental/.repository').mkdir(parents=True)
            ancestor=native.write(root/'ancestor.json',dict(backupId='unconfigured',parentPointPins=[]))
            parent=native.write(root/'full/.repository/point.json',dict(backupId='p',parentPointPins=[ancestor]))
            native.write(root/'incremental/.repository/point.json',dict(backupId='i',parentPointPins=[parent]))
            points={'p':dict(applicationId='a',sourceConfigRef='s',fileStorage=[{'id':28}]),
                    'i':dict(applicationId='a',sourceConfigRef='s')}
            owner=dict(sources={'s':dict(recoveryPoints={},archiveRoots=[folder],
                archiveCatalogue=dict(maximumPointFiles=10))})
            self.assertEqual(native.resolve_point_policy(points,'i',owner)['fileStorage'],[{'id':28}])
            self.assertNotIn('parentBackupId',points['i'])
            native.write(root/'full/.repository/point.json',dict(backupId='other',parentPointPins=[]))
            with self.assertRaisesRegex(native.PreparationError,'PREPARE_POINT_CHANGED'):
                native.resolve_point_policy(points,'i',owner)
    def test_real_pinned_parent_is_used_without_manual_parent_field(self):
        with tempfile.TemporaryDirectory() as folder:
            parent=native.write(Path(folder)/'parent.json',dict(parentPointPins=[]))
            child=native.write(Path(folder)/'child.json',dict(parentPointPins=[parent]))
            points={'p':dict(applicationId='a',sourceConfigRef='s',fileStorage=[{'id':28}]),
                    'i':dict(applicationId='a',sourceConfigRef='s')}
            owner=dict(sources={'s':dict(recoveryPoints={'p':parent,'i':child})})
            self.assertEqual(native.resolve_point_policy(points,'i',owner)['fileStorage'],[{'id':28}])
            Path(parent['path']).write_bytes(b'changed')
            with self.assertRaisesRegex(native.PreparationError,'PREPARE_POINT_CHANGED'):
                native.resolve_point_policy(points,'i',owner)
    def test_inherits_matching_parent(self):
        points={'p':dict(applicationId='a',sourceConfigRef='s',fileStorage=[{'id':28}]),
                'i':dict(applicationId='a',sourceConfigRef='s',parentBackupId='p')}
        self.assertEqual(native.resolve_point_policy(points,'i')['fileStorage'],[{'id':28}])
        self.assertNotIn('fileStorage',points['i'])
    def test_rejects_wrong_source_and_cycle(self):
        points={'p':dict(applicationId='a',sourceConfigRef='x'),
                'i':dict(applicationId='a',sourceConfigRef='s',parentBackupId='p')}
        with self.assertRaises(native.PreparationError):native.resolve_point_policy(points,'i')
        points['p'].update(sourceConfigRef='s',parentBackupId='i')
        with self.assertRaises(native.PreparationError):native.resolve_point_policy(points,'i')

if __name__=='__main__':unittest.main()
