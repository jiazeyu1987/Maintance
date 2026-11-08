"""Exact target59 empty-stage continuation uses real directory evidence."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest


def identity(path):
    info=path.lstat()
    return [getattr(info,k) for k in ('st_dev','st_ino','st_mode','st_nlink','st_uid','st_gid','st_size','st_mtime_ns','st_ctime_ns')]


class EpochResume(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.epoch=self.root/'epochs';self.epoch.mkdir(mode=0o700)
        self.paths=[self.root/name for name in ('owner.json','control.json','previous.json','audit')]
        self.candidate=dict(host='172.30.30.59',targetConfigRef='main59',service='main59.service',sourceCommit='a'*40,
            oldControlPid=5885,oldControlPin={'sha256':'oldcontrol'},oldOwnerPin={'sha256':'oldowner'},oldActiveReceiptPin={'sha256':'oldreceipt'},
            targetBackupEpochPolicy={'root':str(self.epoch)})
        self.current=dict(host='172.30.30.59',targetConfigRef='main59',service='main59.service',sourceCommit='a'*40,pid=5885,
            controlPin=self.candidate['oldControlPin'],ownerPin=self.candidate['oldOwnerPin'],actualReceiptPin=self.candidate['oldActiveReceiptPin'],
            oldPackagePin={'sha256':'oldpackage'},newPackagePin={'sha256':'newpackage'},epochRoot=str(self.epoch),epochRootIdentity=identity(self.epoch),
            epochEntries=[],businessSnapshot={'container':'unchanged'},fstabPin={'sha256':'fstab'},mounts=['mount'],
            absentPaths={str(p):False for p in self.paths},newDropins=[],retainedCount=1759,retainedPinsSha256='d'*64)
        self.proof=dict(schemaVersion='TaskAutomatic59EmptyEpochResume/v1',observation=copy.deepcopy(self.current),
            originalInternalExceptionUnavailable=True,originalErrorCode='EPOCH_INITIALIZATION_FAILED',
            localEvidencePins=[dict(path='error',bytes=100,sha256='a'*64),dict(path='public',bytes=100,sha256='b'*64),dict(path='private',bytes=100,sha256='c'*64)])

    def verify(self):
        from automatic_target_epoch_resume import verify_empty_epoch_stage_resume
        return verify_empty_epoch_stage_resume(self.proof,self.candidate,self.current)

    def test_exact_empty_stage_is_read_only(self):
        before=identity(self.epoch)
        self.verify()
        self.assertEqual(identity(self.epoch),before)
        self.assertEqual(list(self.epoch.iterdir()),[])

    def test_recreated_empty_root_rejected(self):
        self.epoch.rmdir();self.epoch.mkdir(mode=0o700)
        with self.assertRaisesRegex(ValueError,'EPOCH_RESUME_ROOT_CHANGED'):self.verify()

    def test_existing_event_cannot_reinitialize(self):
        (self.epoch/'event.json').write_text('{}',encoding='utf-8')
        with self.assertRaisesRegex(ValueError,'EPOCH_RESUME_ROOT_CHANGED'):self.verify()

    def test_config_created_after_observation_blocks(self):
        self.paths[0].write_text('{}',encoding='utf-8')
        with self.assertRaisesRegex(ValueError,'EPOCH_RESUME_ACTIVATION_ALREADY_STARTED'):self.verify()

    def test_wrong_target_not_58_resume(self):
        self.candidate['host']='172.30.30.58'
        with self.assertRaisesRegex(ValueError,'EPOCH_RESUME_TARGET_INVALID'):self.verify()

    def test_runtime_or_original_pins_or_dropin_drift_blocks(self):
        for key,value in [('pid',5886),('businessSnapshot',{}),('mounts',[]),('oldPackagePin',{}),('newPackagePin',{}),('newDropins',[{}]),('retainedPinsSha256','0'*64)]:
            with self.subTest(key=key):
                current=self.current;self.current=copy.deepcopy(current);self.current[key]=value
                with self.assertRaisesRegex(ValueError,'EPOCH_RESUME_OBSERVATION_CHANGED'):self.verify()
                self.current=current

    def test_unknown_internal_exception_cannot_be_rewritten(self):
        self.proof['originalInternalExceptionUnavailable']=False
        with self.assertRaisesRegex(ValueError,'EPOCH_RESUME_FAILURE_PROOF_INVALID'):self.verify()

    def test_local_evidence_bytes_are_verified(self):
        from automatic_target_epoch_resume import load_epoch_resume_proof
        refs=[]
        for i in range(3):
            path=self.root/('evidence-'+str(i));raw=b'EPOCH_INITIALIZATION_FAILED' if i==0 else b'{}';path.write_bytes(raw)
            refs.append(dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()))
        self.proof['localEvidencePins']=refs
        path=self.root/'proof.json';path.write_text(json.dumps(self.proof),encoding='utf-8')
        self.assertEqual(load_epoch_resume_proof(path),self.proof)
        Path(refs[1]['path']).write_bytes(b'{"changed":true}')
        with self.assertRaisesRegex(ValueError,'EPOCH_RESUME_LOCAL_EVIDENCE_CHANGED'):load_epoch_resume_proof(path)


if __name__=='__main__':unittest.main()
