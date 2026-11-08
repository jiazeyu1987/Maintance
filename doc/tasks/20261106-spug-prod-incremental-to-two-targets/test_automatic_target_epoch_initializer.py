"""Linux-only runner: real flock ownership, inherited fd, and immutable events."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import types
import unittest


class EpochInitializer(unittest.TestCase):
    def setUp(self):
        if not sys.platform.startswith('linux'):
            raise RuntimeError('RUN_THIS_SUITE_IN_THE_REAL_LINUX_CONTAINER')
        import fcntl
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.epoch=self.root/'epochs';self.epoch.mkdir(mode=0o700)
        self.lock=os.open(self.root/'source.lock',os.O_CREAT|os.O_EXCL|os.O_RDWR,0o600)
        self.addCleanup(os.close,self.lock);fcntl.flock(self.lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        self.policy=dict(schemaVersion='SourceBackupEpochPolicy/v1',root=str(self.epoch),sourceIdentity='linux-real-test',
            databaseUuid='9f7a672a-ce77-11f1-9f3a-0242ac1ca820',sourceLockPath=str(self.root/'source.lock'))
        self.module=Path(os.environ['TASK_TEST_EPOCH_MODULE']) if 'TASK_TEST_EPOCH_MODULE' in os.environ else Path(os.environ['TASK_TEST_REPOSITORY'])/'ops/recovery/recovery_backup_epoch.py'
        raw=self.module.read_bytes();self.pin=dict(path=str(self.module),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())

    def test_original_inherited_fd_is_rejected_by_real_module(self):
        code='''import importlib.util,json,sys
spec=importlib.util.spec_from_file_location('real_epoch',sys.argv[1]);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
m.initialize(json.loads(sys.argv[2]),int(sys.argv[3]))
'''
        p=subprocess.run([sys.executable,'-B','-c',code,str(self.module),json.dumps(self.policy),str(self.lock)],pass_fds=(self.lock,),capture_output=True)
        self.assertNotEqual(p.returncode,0)
        self.assertIn(b'BACKUP_EPOCH_EXCLUSIVE_LOCK_REQUIRED',p.stderr)
        self.assertEqual(list(self.epoch.iterdir()),[])

    def test_same_pid_initializes_exact_module_once(self):
        from automatic_target_epoch_initializer import initialize_epoch_in_lock_owner
        result=initialize_epoch_in_lock_owner(self.pin,self.policy,self.lock)
        self.assertEqual(result['initializerPid'],os.getpid())
        self.assertEqual(result['modulePin'],self.pin)
        self.assertEqual(result['epoch']['state'],'READY')
        self.assertEqual(len(list(self.epoch.iterdir())),1)
        with self.assertRaisesRegex(ValueError,'BACKUP_EPOCH_ALREADY_INITIALIZED'):
            initialize_epoch_in_lock_owner(self.pin,self.policy,self.lock)

    def test_wrong_module_pin_blocks_without_write(self):
        from automatic_target_epoch_initializer import initialize_epoch_in_lock_owner
        with self.assertRaisesRegex(ValueError,'EPOCH_INITIALIZER_MODULE_CHANGED'):
            initialize_epoch_in_lock_owner(dict(self.pin,sha256='0'*64),self.policy,self.lock)
        self.assertEqual(list(self.epoch.iterdir()),[])

    def test_other_descriptor_does_not_borrow_lock(self):
        from automatic_target_epoch_initializer import initialize_epoch_in_lock_owner
        other=os.open(self.root/'source.lock',os.O_RDWR)
        try:
            with self.assertRaisesRegex(ValueError,'BACKUP_EPOCH_EXCLUSIVE_LOCK_REQUIRED'):
                initialize_epoch_in_lock_owner(self.pin,self.policy,other)
        finally:os.close(other)
        self.assertEqual(list(self.epoch.iterdir()),[])

    def test_nonstdlib_dependency_rejected_before_execution(self):
        from automatic_target_epoch_initializer import initialize_epoch_in_lock_owner
        raw=self.module.read_bytes()+b'\nimport recovery_engine\n';path=self.root/'unexpected-dependency.py';path.write_bytes(raw)
        reference=dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
        with self.assertRaisesRegex(ValueError,'EPOCH_INITIALIZER_DEPENDENCY_CHANGED'):
            initialize_epoch_in_lock_owner(reference,self.policy,self.lock)
        self.assertEqual(list(self.epoch.iterdir()),[])

    def test_old_cached_epoch_module_is_not_used(self):
        from automatic_target_epoch_initializer import initialize_epoch_in_lock_owner
        old=sys.modules.get('recovery_backup_epoch');fake=types.ModuleType('recovery_backup_epoch')
        def forbidden(*args):raise AssertionError('OLD_CACHED_MODULE_WAS_USED')
        fake.initialize=forbidden;sys.modules['recovery_backup_epoch']=fake
        try:
            result=initialize_epoch_in_lock_owner(self.pin,self.policy,self.lock)
        finally:
            if old is None:sys.modules.pop('recovery_backup_epoch',None)
            else:sys.modules['recovery_backup_epoch']=old
        self.assertEqual(result['epoch']['state'],'READY')
        self.assertTrue(result['loadedFromVerifiedSource'])
        self.assertEqual(set(result['dependencyOrigins']),{'datetime','hashlib','json','os','pathlib','re','stat','sys','fcntl'})


if __name__=='__main__':unittest.main()
