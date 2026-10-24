"""Exercise the composed production executor, not the mixin in isolation."""
from pathlib import Path
import threading
import unittest
from unittest.mock import Mock, patch

from intruoyi_executor import IntRuoyiExecutor
from rollback_mixin import RollbackMixin


class RollbackIntegrationTest(unittest.TestCase):
    def executor(self):
        obj = object.__new__(IntRuoyiExecutor)
        obj.lock = threading.RLock()
        obj.c = dict(applicationId='intruoyi', displayName='IntRuoyi', repo='unit', targets={})
        obj.root = Path('.')
        obj.state = dict(jobs=[], packages=[], environments={})
        obj.runtime = Mock()
        obj.ensure_persistence = Mock()
        obj.save = Mock()
        return obj

    def test_all_rollback_hooks_precede_concrete_executor(self):
        for method in ('snapshot', 'submit', 'deploy'):
            self.assertIs(getattr(IntRuoyiExecutor, method), getattr(RollbackMixin, method))

    def test_real_snapshot_advertises_rollback_and_existing_capabilities(self):
        obj = self.executor()
        with patch('intruoyi_executor.active_remote_progress', return_value=False):
            result = obj.snapshot()
        self.assertTrue(result['application']['capabilities']['productionRollback'])
        self.assertTrue(result['application']['capabilities']['buildRelease'])
        self.assertEqual(result['jobs'], [])

    def test_real_submit_routes_preview_to_rollback_worker(self):
        obj = self.executor()
        with patch('rollback_mixin.threading.Thread') as worker:
            job = obj.submit('rollback-preview', dict(applicationId='intruoyi', requestId='preview-integration'), 'operator')
        self.assertEqual(job['action'], 'rollback-preview')
        self.assertEqual(worker.call_args.kwargs['target'], obj.rollback_job)
        obj.save.assert_called_once()


if __name__ == '__main__':
    unittest.main()
