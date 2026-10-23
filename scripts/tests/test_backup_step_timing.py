import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('step_timing', ROOT/'ops/recovery/recovery_step_timing.py')
timing = importlib.util.module_from_spec(spec)
spec.loader.exec_module(timing)


class StepTiming(unittest.TestCase):
    def test_failure_preserves_original_exception_and_writes_failed_boundary(self):
        error = RuntimeError('ACTUAL_STEP_FAILED')
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with self.assertRaises(RuntimeError) as caught:
                with timing.step(root, 'object-restore'):
                    raise error
            self.assertIs(caught.exception, error)
            end = json.loads((root/'timing-object-restore-end.json').read_bytes())
            self.assertFalse(end['completed'])
            self.assertGreaterEqual(end['elapsedSeconds'], 0)

    def test_completed_step_is_exclusive_and_does_not_overwrite_history(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with timing.step(root, 'redis-rebuild'):
                pass
            before = {p.name:p.read_bytes() for p in root.iterdir()}
            self.assertTrue(json.loads(before['timing-redis-rebuild-end.json'])['completed'])
            with self.assertRaises(FileExistsError):
                with timing.step(root, 'redis-rebuild'):
                    self.fail('a duplicate stage must not execute')
            self.assertEqual(before, {p.name:p.read_bytes() for p in root.iterdir()})

    def test_invalid_stage_cannot_escape_its_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, 'STEP_TIMING_NAME_INVALID'):
                with timing.step(directory, '../outside'):
                    self.fail('invalid timing stage must not execute')
            self.assertEqual(list(Path(directory).iterdir()), [])
