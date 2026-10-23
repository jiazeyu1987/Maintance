import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import hashlib

spec = importlib.util.spec_from_file_location('progress', Path(__file__).with_name('smallapp_progress_remote.py'))
progress = importlib.util.module_from_spec(spec)
spec.loader.exec_module(progress)


class PublicProgress(unittest.TestCase):
    def test_real_journals_order_duration_and_secret_exclusion(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            request = dict(operationId='test-operation-123', action='RESTORE')
            directory = root / 'recovery-operations' / request['operationId']
            directory.mkdir(parents=True)
            def write(path, data):
                path.write_text(json.dumps(data), encoding='utf-8')
            write(directory/'request.json', request)
            write(directory/'timing-z-start.json', dict(stage='z', startedAt='2026-10-22T01:00:00Z'))
            write(directory/'timing-z-end.json', dict(finishedAt='2026-10-22T01:00:04Z', elapsedSeconds=4, completed=False))
            write(directory/'timing-a-start.json', dict(stage='a', startedAt='2026-10-22T02:00:00Z'))
            write(directory/'event-0001.json', dict(stage='DATA_STARTED', at='2026-10-22T01:00:00Z', password='never-return-this'))
            write(directory/'result.json', dict(state='FAILED_RETAINED', startedAt='2026-10-22T01:00:00Z', finishedAt='2026-10-22T02:00:01Z', secret='never-return-this'))
            result = progress.project(root, request)
            self.assertEqual([s['name'] for s in result['steps']], ['z', 'a'])
            self.assertEqual(result['steps'][0]['state'], 'FAILED')
            self.assertEqual(result['steps'][0]['elapsedSeconds'], 4)
            self.assertEqual(result['steps'][1]['state'], 'UNCONFIRMED')
            self.assertIsNone(result['steps'][1]['finishedAt'])
            self.assertIsNone(result['steps'][1]['elapsedSeconds'])
            self.assertFalse(result['percentageAvailable'])
            self.assertNotIn('never-return-this', json.dumps(result))
            with self.assertRaisesRegex(ValueError, 'PROGRESS_REQUEST_MISMATCH'):
                progress.project(root, dict(request, sourceConfigRef='different'))

    def test_backup_operation_directory_uses_exact_digest(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)
            request=dict(operationId='backup-test-1234', action='FULL')
            directory=root/'repository-operations'/hashlib.sha256(request['operationId'].encode()).hexdigest()
            directory.mkdir(parents=True)
            (directory/'request.json').write_text(json.dumps(request),encoding='utf-8')
            result=progress.project(root,request)
            self.assertEqual(result['operationId'],request['operationId'])
            self.assertEqual(result['state'],'RUNNING')
            self.assertEqual(result['steps'],[])

    def test_path_injection_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'PROGRESS_OPERATION_INVALID'):
            progress.project('/tmp',dict(operationId='../another-operation',action='RESTORE'))

    def test_missing_step_end_is_unconfirmed_for_all_terminal_outcomes(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            request = dict(operationId='terminal-operation-123', action='RESTORE')
            directory = root / 'recovery-operations' / request['operationId']
            directory.mkdir(parents=True)
            (directory / 'request.json').write_text(json.dumps(request), encoding='utf-8')
            (directory / 'timing-step-start.json').write_text(json.dumps(
                dict(stage='database-restore', startedAt='2026-10-22T01:00:00Z')), encoding='utf-8')
            self.assertEqual(progress.project(root, request)['steps'][0]['state'], 'RUNNING')
            for state in ('SUCCEEDED', 'FAILED', 'FAILED_RETAINED', 'TERMINAL_UNKNOWN'):
                (directory / 'result.json').write_text(json.dumps(dict(state=state)), encoding='utf-8')
                step = progress.project(root, request)['steps'][0]
                self.assertEqual(step['state'], 'UNCONFIRMED')
                self.assertIsNone(step['finishedAt'])
                self.assertIsNone(step['elapsedSeconds'])


if __name__ == '__main__':
    unittest.main()
