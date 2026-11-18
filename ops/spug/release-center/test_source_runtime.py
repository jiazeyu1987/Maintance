import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
import release_backup_source as source


class SourceRuntimeTests(unittest.TestCase):
    def test_registered_python_and_environment_execute_stage(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            control = {'pythonPin': {'path': sys.executable},
                       'environment': {'SOURCE_RUNTIME_TEST': 'registered'}}
            path = root / 'control.json'
            raw = json.dumps(control).encode()
            path.write_bytes(raw)
            pin = {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
            program = ('import os,sys\n'
                       'def stage(binding,candidate,pin):\n'
                       ' return {"python":sys.executable,"environment":os.environ["SOURCE_RUNTIME_TEST"],"releaseTag":candidate["releaseTag"]}\n')
            result = source.stage_in_runtime({'pythonPath': sys.executable},
                {'releaseTag': 'test'}, pin, program)
            self.assertEqual(result, {'python': sys.executable, 'environment': 'registered', 'releaseTag': 'test'})
            with self.assertRaisesRegex(ValueError, 'SOURCE_STAGE_PROCESS_FAILED'):
                source.stage_in_runtime({'pythonPath': sys.executable}, {}, pin,
                                        'raise RuntimeError("private-error")')
            with self.assertRaisesRegex(ValueError, 'SOURCE_PYTHON_MISMATCH'):
                source.stage_in_runtime({'pythonPath': 'wrong-python'}, {}, pin, program)
            path.write_bytes(b'{}')
            with self.assertRaisesRegex(ValueError, 'SOURCE_BINDING_PIN_CHANGED'):
                source.stage_in_runtime({'pythonPath': sys.executable}, {}, pin, program)

if __name__ == '__main__': unittest.main()
