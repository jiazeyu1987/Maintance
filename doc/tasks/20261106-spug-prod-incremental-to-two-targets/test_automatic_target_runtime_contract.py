import hashlib
import json
import os
from pathlib import Path
import sys
import unittest

from automatic_target_runtime_contract import verify_control_runtime,observe_worker_environment


class RuntimeContract(unittest.TestCase):
    def setUp(self):
        repository=os.environ.get('TASK_TEST_REPOSITORY') or str(Path(__file__).resolve().parents[3])
        self.resources=Path(repository)/'backend/src/main/resources'
        self.module=self.resources/'recovery_control_smallapp_native.py'
        raw=self.module.read_bytes()
        self.module_pin=dict(path=str(self.module),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
        self.env=dict(LANG='C.UTF-8',PATH='/deliberately-different-no-programs',PYTHONDONTWRITEBYTECODE='1',PYTHONPATH=str(self.resources))
        self.argv=[sys.executable,'-B','control_entry.py','serve','--config-pin','fixed-pin']

    def test_parent_inherits_distinct_lang_and_path(self):
        parent=dict(self.env,LANG='different-parent-locale',PATH='different-parent-path')
        value=verify_control_runtime(parent,self.env,self.argv,self.argv)
        self.assertEqual(value['inheritedParentDifferences'],['LANG','PATH'])

    def test_parent_module_path_drift_rejected(self):
        with self.assertRaisesRegex(ValueError,'CONTROL_PYTHONPATH_CHANGED'):
            verify_control_runtime(dict(self.env,PYTHONPATH='/other'),self.env,self.argv,self.argv)

    def test_parent_argv_drift_rejected(self):
        with self.assertRaisesRegex(ValueError,'CONTROL_ARGV_CHANGED'):
            verify_control_runtime(self.env,self.env,self.argv+['extra'],self.argv)

    def test_real_worker_uses_exact_configured_environment_and_real_module(self):
        value=observe_worker_environment(sys.executable,self.env,self.module_pin)
        expected=hashlib.sha256(json.dumps(self.env,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        self.assertEqual(value['environmentSha256'],expected)
        self.assertEqual(value['modulePin'],self.module_pin)
        self.assertTrue(value['bytecodeDisabled'])

    def test_wrong_module_pin_is_rejected_after_actual_child_import(self):
        with self.assertRaisesRegex(ValueError,'WORKER_MODULE_CHANGED'):
            observe_worker_environment(sys.executable,self.env,dict(self.module_pin,sha256='0'*64))

    def test_bad_pythonpath_does_not_substitute_another_module(self):
        with self.assertRaisesRegex(ValueError,'WORKER_ENVIRONMENT_PROBE_FAILED'):
            observe_worker_environment(sys.executable,dict(self.env,PYTHONPATH=str(self.resources/'absent')),self.module_pin)


if __name__=='__main__':unittest.main()
