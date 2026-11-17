"""Linux contract integration: real files, flock and controller /proc identity.

The systemd and Docker boundaries are local test doubles, not a deployed E2E.
"""
import fcntl
import hashlib
import json
import shlex
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from release_backup_source import synchronize


class ActivationTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.root=Path(self.temp.name)
        self.entry=self.root/'control_entry.py'
        self.entry.write_text('import time\ntime.sleep(60)\n')
        self.lock=self.root/'source.lock'
        self.old=self.pin('old.json', {'sourceEpochPolicies':{'source':{'sourceLockPath':str(self.lock)}}})
        self.new=self.pin('new.json', {'sourceEpochPolicies':{'source':{'sourceLockPath':str(self.lock)}}})
        self.capture=self.pin('capture.json', {})
        self.env=self.root/'.env';self.env.write_bytes(b'IMAGE_TAG=v1\n')
        envpin=self.pin('runtime.env', b'IMAGE_TAG=v1\n')
        self.generation=self.root/'generations'/'v1';self.generation.mkdir(parents=True)
        self.receipt={'releaseTag':'v1','originalControlPin':self.old,'controlPin':self.new,
                      'capturePin':self.capture,'environmentPin':envpin,'actualServices':[
                          {'role':'backend','id':'container-new','imageId':'image-new'}]}
        (self.generation/'staging-receipt.json').write_text(json.dumps(self.receipt))
        self.binding=dict(sourceRef='source',engineRoot=str(self.root),generationRoot=str(self.root/'generations'),
            environmentFile=str(self.env),composeFile=str(self.root/'compose.yml'),pythonPath=sys.executable,
            controlEntryPath=str(self.entry),serviceName='source.service',dropInDirectory=str(self.root/'source.service.d'),
            containers={'backend':'backend','frontend':'frontend'})
        self.proc=None;self.starts=0;self.fail_restart=False;self.wrong_pin=False
        self.start(self.old)

    def pin(self, name, value):
        data=value if isinstance(value,bytes) else json.dumps(value).encode()
        path=self.root/name;path.write_bytes(data)
        return {'path':str(path),'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}

    def start(self,pin):
        if self.proc:self.proc.terminate();self.proc.wait()
        self.proc=subprocess.Popen([sys.executable,str(self.entry),'serve','--config-pin',json.dumps(pin)])
        for _ in range(100):
            if str(self.entry).encode() in (Path('/proc')/str(self.proc.pid)/'cmdline').read_bytes():break
            time.sleep(.001)
        self.starts+=1

    def command(self,args):
        if args[1]=='show':return str(self.proc.pid)
        if args[1]=='restart':
            if self.fail_restart:raise RuntimeError('SYSTEMD_RESTART_FAILED')
            text=next(Path(self.binding['dropInDirectory']).glob('*.conf')).read_text()
            command=shlex.split(text.split('ExecStart=')[-1].strip())
            self.start(self.old if self.wrong_pin else json.loads(command[-1]))
        return ''

    def inspect(self,name):return {'Id':'container-new','Image':'image-new','State':{'Running':True}}
    def sync(self):return synchronize({'backupSourceBinding':self.binding,'backend':'backend','frontend':'frontend'},{'releaseTag':'v1'},run=self.command,inspect=self.inspect)

    def tearDown(self):
        if self.proc:self.proc.terminate();self.proc.wait()
        self.temp.cleanup()

    def test_activation_reads_real_process_pin_and_retry_does_not_restart(self):
        self.assertEqual(self.sync()['status'],'SYNCHRONIZED')
        self.assertEqual(self.starts,2)
        self.assertEqual(self.sync()['status'],'SYNCHRONIZED')
        self.assertEqual(self.starts,2)

    def test_restart_failure_is_retryable_and_never_marks_success(self):
        self.fail_restart=True
        with self.assertRaisesRegex(RuntimeError,'RESTART_FAILED'):self.sync()
        self.assertFalse((self.generation/'activation-receipt.json').exists())
        self.fail_restart=False
        self.assertEqual(self.sync()['status'],'SYNCHRONIZED')

    def test_controller_loading_wrong_pin_is_failure(self):
        self.wrong_pin=True
        with self.assertRaisesRegex(ValueError,'ACTIVATION_PIN_MISMATCH'):self.sync()
        self.assertFalse((self.generation/'activation-receipt.json').exists())

    def test_active_source_lock_blocks_before_restart(self):
        with self.lock.open('a+b') as lock:
            fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
            with self.assertRaises(BlockingIOError):self.sync()
        self.assertEqual(self.starts,1)

    def test_changed_container_rejects_completed_stage(self):
        self.inspect=lambda name:{'Id':'another','Image':'image-new','State':{'Running':True}}
        with self.assertRaisesRegex(ValueError,'CONTAINER_CHANGED'):self.sync()
        self.assertEqual(self.starts,1)

    def test_changed_pin_rejects_before_activation(self):
        Path(self.new['path']).write_text('{}')
        with self.assertRaisesRegex(ValueError,'PIN_CHANGED'):self.sync()
        self.assertEqual(self.starts,1)

    def test_other_application_binding_rejected(self):
        self.binding['containers']['backend']='unrelated'
        with self.assertRaisesRegex(ValueError,'APPLICATION_MISMATCH'):self.sync()

    def test_older_release_replaces_same_dropin_and_keeps_previous_evidence(self):
        self.sync()
        previous=self.new
        self.new=self.pin('next.json', {'sourceEpochPolicies':{'source':{'sourceLockPath':str(self.lock)}}})
        next_generation=self.root/'generations'/'v0';next_generation.mkdir()
        receipt=dict(self.receipt,releaseTag='v0',originalControlPin=previous,controlPin=self.new)
        (next_generation/'staging-receipt.json').write_text(json.dumps(receipt))
        result=synchronize({'backupSourceBinding':self.binding,'backend':'backend','frontend':'frontend'},
                           {'releaseTag':'v0'},run=self.command,inspect=self.inspect)
        self.assertEqual(result['controlPin'],self.new)
        self.assertEqual(len(list(Path(self.binding['dropInDirectory']).glob('*.conf'))),1)
        self.assertTrue((next_generation/'previous-dropin.json').exists())


if __name__=='__main__':unittest.main()
