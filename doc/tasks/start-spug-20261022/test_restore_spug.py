import importlib.util
import tempfile
import unittest
from pathlib import Path


class RestoreContract(unittest.TestCase):
    def setUp(self):
        spec = importlib.util.spec_from_file_location('restore', Path(__file__).with_name('restore_spug.py'))
        self.restore = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.restore)

    def test_refuse_existing_destination_and_live_resources(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / 'new'
            for names, volumes, occupied in [(['intruoyi-spug-transfer-spug-1'], [], False),
                                             ([], ['intruoyi-spug-transfer_data'], False),
                                             ([], [], True)]:
                with self.assertRaises(RuntimeError):
                    self.restore.validate_destination(root, names, volumes, occupied)
            root.mkdir()
            with self.assertRaises(RuntimeError):
                self.restore.validate_destination(root, [], [], False)

    def test_c_drive_compose_preserves_data_and_local_binding(self):
        config = self.restore.make_config(Path('C:/Spug/runtime'), Path('C:/Spug/package'),
                                          {'spugImage': 'app', 'dbImage': 'db'},
                                          {'SPUG_DB_PASSWORD': 'test-only', 'SPUG_DB_ROOT_PASSWORD': 'test-only'})
        app = config['services']['spug']
        self.assertEqual(app['ports'], ['127.0.0.1:18080:80'])
        self.assertEqual(len(config['volumes']), 5)
        self.assertTrue(all('D:' not in v and 'E:' not in v for v in app['volumes']))
        self.assertIn('service:/data/spug', app['volumes'])
        self.assertNotIn('ports', config['services']['db'])


if __name__ == '__main__':
    unittest.main()
