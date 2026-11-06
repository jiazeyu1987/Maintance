"""Check exact retained-start provenance before the authorized original storage stop."""
import copy
import hashlib
import json
import unittest
from quiesce_failed_health_storage import GUARDS

class QuiescenceGuardTests(unittest.TestCase):
    def setUp(self):
        def digest(v):return hashlib.sha256(json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        def need(value,code):
            if not value:raise ValueError(code)
        namespace=dict(digest=digest,need=need,target={'dockerPin':{'path':'/usr/bin/docker'}})
        exec(compile(GUARDS,'quiescence-guards','exec'),namespace)
        self.validate=namespace['validate_started_storage']
        self.row={'Id':'a'*64,'State':dict(Running=True,Paused=False,Restarting=False,Pid=2,StartedAt='2026-11-06T06:48:45.468620213Z')}
        self.invocation=dict(schemaVersion='RecoveryDataInvocation/v1',operationId='failed',
            argvSha256=digest(['/usr/bin/docker','--host','unix:///var/run/docker.sock','start','a'*64]),
            mutation=True,state='SUCCEEDED',actualExitCode=0,startedAt='2026-11-06T06:48:44Z',finishedAt='2026-11-06T06:48:46Z')
        self.finished='2026-11-06T06:48:54Z'
    def test_only_same_operation_successful_exact_start_accepted(self):
        self.assertEqual({'path':'proof'},self.validate('failed',self.row,[({'path':'proof'},self.invocation)],self.finished))
    def test_other_command_operation_unknown_or_failed_rejected(self):
        for key,value in [('operationId','other'),('argvSha256','0'*64),('mutation',False),('state','TERMINAL_UNKNOWN'),('actualExitCode',1)]:
            invocation=dict(self.invocation,**{key:value})
            with self.assertRaisesRegex(ValueError,'FAILED_STORAGE_START_NOT_PROVEN'):
                self.validate('failed',self.row,[({},invocation)],self.finished)
    def test_ambiguous_duplicate_start_rejected(self):
        with self.assertRaisesRegex(ValueError,'FAILED_STORAGE_START_NOT_PROVEN'):
            self.validate('failed',self.row,[({},self.invocation),({},self.invocation)],self.finished)
    def test_external_restart_before_or_after_native_start_rejected(self):
        for stamp in ('2026-11-06T06:48:43Z','2026-11-06T06:48:47Z'):
            self.row['State']['StartedAt']=stamp
            with self.assertRaisesRegex(ValueError,'FAILED_STORAGE_START_TIME_CHANGED'):
                self.validate('failed',self.row,[({},self.invocation)],self.finished)
    def test_failed_stop_cannot_be_treated_as_quiescent(self):
        for key,value in [('Running',False),('Pid',0),('Paused',True),('Restarting',True)]:
            row=copy.deepcopy(self.row);row['State'][key]=value
            with self.assertRaisesRegex(ValueError,'FAILED_STORAGE_NOT_STABLE'):
                self.validate('failed',row,[({},self.invocation)],self.finished)

if __name__=='__main__':unittest.main()
