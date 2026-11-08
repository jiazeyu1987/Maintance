import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import uuid

import automatic_target_history_guard as guard


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True, separators=(',', ':')), encoding='utf-8')
    raw=path.read_bytes()
    return dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())


class AuditAppend(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name).resolve()
        self.ledger=self.root/'ledger';self.op=self.ledger/'smallapp-known'
        self.query=self.op/'queries';self.query.mkdir(parents=True)
        self.request=dict(operationId=self.op.name,sourceConfigRef='source-known',action='RESTORE')
        save(self.op/'request.json',self.request)
        self.owner=save(self.root/'operations'/self.op.name/'result.json',dict(operationId=self.op.name,requestId=self.op.name,action='RESTORE',state='FAILED_RETAINED',actualExitCode=1))
        owner_config=save(self.root/'owner-config.json',dict(schemaVersion='RecoveryMinimalConfiguration/v1',operationsRoot=str(self.root/'operations')))
        save(self.op/'selection.json',dict(ownerConfigurationPin=owner_config))
        self.before=guard.history_snapshot([self.ledger])
        self.record=dict(operationId=self.op.name,requestSha256=hashlib.sha256(json.dumps(self.request,sort_keys=True,separators=(',', ':')).encode()).hexdigest(),ownerResultPin=self.owner,resolutionPins=[],resourceReleaseError=None,ownerActualExitCode=1,
            result=dict(schemaVersion='SmallAppBackupUiResult/v1',operationId=self.op.name,action='RESTORE',state='FAILED',errorCode='ORIGINAL_FAILED',logRefs=[],resultRef=None),observedAt='2026-11-07T18:02:19+00:00')

    def append(self, record=None, name=None):
        path=self.query/(name or (uuid.uuid4().hex+'.json'))
        process=subprocess.run([sys.executable,'-c','import json,pathlib,sys;pathlib.Path(sys.argv[1]).write_text(json.dumps(json.loads(sys.argv[2]),sort_keys=True,separators=(",",":")),encoding="utf-8")',str(path),json.dumps(record or self.record)],capture_output=True)
        self.assertEqual(process.returncode,0,process.stderr)
        return path

    def verify(self):
        return guard.verify_query_append(self.before,guard.history_snapshot([self.ledger]),self.ledger,'source-known')

    def test_real_child_append_is_fully_bound(self):
        path=self.append()
        result=self.verify()
        self.assertEqual([x['path'] for x in result['queryPins']],[str(path)])

    def test_unchanged_tree_passes(self):
        self.assertEqual(self.verify()['queryPins'],[])

    def test_prior_file_change_is_rejected(self):
        self.append();save(self.op/'request.json',dict(self.request,action='FULL'))
        with self.assertRaisesRegex(ValueError,'HISTORY_ORIGINAL_CHANGED'):self.verify()

    def test_same_bytes_replaced_file_is_rejected(self):
        path=self.op/'request.json';raw=path.read_bytes();other=self.root/'replacement';other.write_bytes(raw);other.replace(path)
        with self.assertRaisesRegex(ValueError,'HISTORY_ORIGINAL_CHANGED'):self.verify()

    def test_extra_non_query_file_rejected(self):
        self.append();save(self.op/'new-result.json',{})
        with self.assertRaisesRegex(ValueError,'HISTORY_APPEND_PATH'):self.verify()

    def test_new_foreign_source_operation_rejected(self):
        value=dict(self.record,operationId='foreign')
        self.append(value)
        with self.assertRaisesRegex(ValueError,'HISTORY_QUERY_BINDING'):self.verify()

    def test_wrong_request_digest_rejected(self):
        self.append(dict(self.record,requestSha256='0'*64))
        with self.assertRaisesRegex(ValueError,'HISTORY_QUERY_BINDING'):self.verify()

    def test_wrong_owner_pin_rejected(self):
        self.append(dict(self.record,ownerResultPin=dict(self.owner,sha256='0'*64)))
        with self.assertRaisesRegex(ValueError,'HISTORY_QUERY_PIN'):self.verify()

    def test_same_operation_unselected_owner_result_rejected(self):
        foreign=save(self.root/'unselected-result.json',json.loads(Path(self.owner['path']).read_bytes()))
        self.append(dict(self.record,ownerResultPin=foreign))
        with self.assertRaisesRegex(ValueError,'HISTORY_QUERY_OWNER_BINDING'):self.verify()

    def test_wrong_result_operation_rejected(self):
        self.append(dict(self.record,result=dict(self.record['result'],operationId='foreign')))
        with self.assertRaisesRegex(ValueError,'HISTORY_QUERY_BINDING'):self.verify()

    def test_nonterminal_result_rejected(self):
        self.append(dict(self.record,result=dict(self.record['result'],state='RUNNING')))
        with self.assertRaisesRegex(ValueError,'HISTORY_QUERY_BINDING'):self.verify()

    def test_query_directory_replaced_rejected(self):
        self.query.rename(self.root/'oldqueries');self.query.mkdir();self.append()
        with self.assertRaisesRegex(ValueError,'HISTORY_(DIRECTORY|ORIGINAL)_CHANGED'):self.verify()

    def test_missing_before_is_not_reconstructed(self):
        self.append()
        with self.assertRaisesRegex(ValueError,'HISTORY_BEFORE_REQUIRED'):
            guard.verify_query_append({},guard.history_snapshot([self.ledger]),self.ledger,'source-known')

    def test_invalid_filename_rejected(self):
        self.append(name='unbound.json')
        with self.assertRaisesRegex(ValueError,'HISTORY_APPEND_PATH'):self.verify()


class InstallerOrdering(unittest.TestCase):
    def test_constructor_never_reconciles_ledger(self):
        from automatic_targets_install_script import GATE
        self.assertNotIn('require_source_idle',GATE)

    def test_admission_precedes_host_lock_and_final_snapshot(self):
        from automatic_targets_install_script import SCRIPT,SOURCE_IDLE
        self.assertEqual(SOURCE_IDLE.count('.require_source_idle('),1)
        self.assertLess(SCRIPT.index('source_idle='),SCRIPT.index('with _host_lock():'))
        self.assertLess(SCRIPT.index('with _host_lock():'),SCRIPT.index('history=history_identity()'))

    def test_resume_requires_bound_failure_proof(self):
        from automatic_targets_install_script import SCRIPT
        self.assertIn('RESUME_STAGE_PROOF_REQUIRED',SCRIPT)
        self.assertIn('RESUME_STAGE_FILE_SET_CHANGED',SCRIPT)
        self.assertIn('read(RESUME_PROOF[\'constructorEvidencePin\'])',SCRIPT)


class SavedSnapshot(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name).resolve();self.scope=self.root/'history';self.scope.mkdir()
        self.payload=self.scope/'incremental.sql';self.payload.write_bytes(b'unchanged payload\n'*10000)
        self.rows=guard.history_snapshot([self.scope])

    def test_unchanged_payload_verified_without_reopening_content(self):
        snapshot=self.root/'snapshot.json';save(snapshot,self.rows)
        script='''import json,sys,pathlib
import automatic_target_history_guard as guard
rows=json.loads(pathlib.Path(sys.argv[1]).read_bytes());payload=sys.argv[3]
def block(event,args):
 if event=='open' and str(args[0])==payload:raise AssertionError('PAYLOAD_REOPENED')
sys.addaudithook(block)
guard.verify_saved_snapshot(rows,[pathlib.Path(sys.argv[2])])
'''
        p=subprocess.run([sys.executable,'-B','-c',script,str(snapshot),str(self.scope),str(self.payload)],capture_output=True)
        self.assertEqual(p.returncode,0,p.stderr.decode())

    def test_followup_snapshot_reuses_only_exact_unchanged_file_identity(self):
        snapshot=self.root/'snapshot.json';save(snapshot,self.rows)
        script='''import json,sys,pathlib
import automatic_target_history_guard as guard
rows=json.loads(pathlib.Path(sys.argv[1]).read_bytes());payload=sys.argv[3]
def block(event,args):
 if event=='open' and str(args[0])==payload:raise AssertionError('PAYLOAD_REOPENED')
sys.addaudithook(block)
assert guard.history_snapshot([pathlib.Path(sys.argv[2])],baseline=rows)==rows
'''
        p=subprocess.run([sys.executable,'-B','-c',script,str(snapshot),str(self.scope),str(self.payload)],capture_output=True)
        self.assertEqual(p.returncode,0,p.stderr.decode())

    def test_followup_snapshot_rejects_changed_existing_payload(self):
        self.payload.write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError,'HISTORY_ORIGINAL_CHANGED'):guard.history_snapshot([self.scope],baseline=self.rows)

    def test_changed_payload_with_restored_mtime_rejected(self):
        before=self.payload.stat();self.payload.write_bytes(b'changed!');os.utime(self.payload,ns=(before.st_atime_ns,before.st_mtime_ns))
        with self.assertRaisesRegex(ValueError,'SAVED_HISTORY_IDENTITY_CHANGED'):guard.verify_saved_snapshot(self.rows,[self.scope])

    def test_added_file_rejected(self):
        (self.scope/'unrelated.json').write_bytes(b'{}')
        with self.assertRaisesRegex(ValueError,'SAVED_HISTORY_ENTRY_SET_CHANGED'):guard.verify_saved_snapshot(self.rows,[self.scope])

    def test_removed_file_rejected(self):
        self.payload.unlink()
        with self.assertRaisesRegex(ValueError,'SAVED_HISTORY_ENTRY_SET_CHANGED'):guard.verify_saved_snapshot(self.rows,[self.scope])

    def test_replaced_identical_payload_rejected(self):
        replacement=self.root/'replacement';replacement.write_bytes(self.payload.read_bytes());replacement.replace(self.payload)
        with self.assertRaisesRegex(ValueError,'SAVED_HISTORY_IDENTITY_CHANGED'):guard.verify_saved_snapshot(self.rows,[self.scope])


class FinalizationContract(unittest.TestCase):
    def test_finalization_has_no_restart_stage_or_source_idle(self):
        from automatic_target_finalize_script import finalization_script
        import ast
        text=finalization_script();tree=ast.parse(text)
        self.assertNotIn('require_source_idle(',text)
        self.assertNotIn("'restart'",text)
        self.assertNotIn('engine.mkdir',text)
        self.assertNotIn('history_snapshot(',text)
        self.assertNotIn('initialize(',text)
        self.assertTrue(any(isinstance(x,ast.Call) and isinstance(x.func,ast.Name) and x.func.id=='verify_saved_snapshot' for x in ast.walk(tree)))


if __name__=='__main__':unittest.main()
