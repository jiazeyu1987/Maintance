"""Real Linux process/flock test. Run in the pinned local Python Linux image."""
import multiprocessing
import os
from pathlib import Path
import tempfile
import unittest


def holder(root, entered, release):
    from operation_journal import execute
    staging=Path(root)/'attempts'/'JOB-0123456789';staging.mkdir(parents=True)
    payload=dict(profile=dict(stagingRoot=str(staging),operationLockRoot=root),operationId='OP-'+'a'*20,
                 workflowJobId='JOB-0123456789',action='deploy')
    def dispatch(value):
        entered.set()
        if not release.wait(15): raise RuntimeError('test synchronization timed out')
        return dict(status='succeeded')
    execute(payload,dispatch)


@unittest.skipIf(os.name == 'nt', 'Linux flock requires the local Linux test container')
class RealLockTests(unittest.TestCase):
    def test_another_controller_cannot_clean_while_deployment_is_running(self):
        from operation_journal import execute
        with tempfile.TemporaryDirectory() as root:
            entered=multiprocessing.Event(); release=multiprocessing.Event()
            process=multiprocessing.Process(target=holder,args=(root,entered,release));process.start()
            try:
                self.assertTrue(entered.wait(10),'deployment did not enter dispatch')
                payload=dict(profile=dict(stagingRoot=root),operationId='OP-'+'b'*20,
                             workflowJobId='JOB-9876543210',action='artifact-auto-clean')
                effects=[]
                with self.assertRaises(BlockingIOError):
                    execute(payload,lambda value:effects.append('deleted'))
                self.assertEqual(effects,[])
                self.assertFalse((Path(root)/'.operations'/(payload['operationId']+'.json')).exists())
                release.set();process.join(10)
                self.assertEqual(process.exitcode,0)
                result=execute(payload,lambda value:dict(status='succeeded'))
                self.assertEqual(result['status'],'succeeded')
            finally:
                release.set();process.join(5)
                if process.is_alive():process.terminate();process.join(5)


if __name__=='__main__': unittest.main()
