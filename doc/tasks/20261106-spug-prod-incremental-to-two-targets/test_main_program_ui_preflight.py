"""Pure gate tests; these do not stand in for actual runtime acceptance."""
import copy
import unittest
from prepare_main_program_ui_preflight import validate_runtime, plan_for_gate


class MainProgramUiPreflightTests(unittest.TestCase):
    def setUp(self):
        self.value = dict(sourceIdle=True, workerPids=[], activeReservation=False,
            servicesRunning=True, serviceCount=5, mainSourceMatchesTarget=True,
            sourceIdentity='source', databaseUuid='uuid', epochId='epoch',
            health={role: dict(ready=True, httpStatus=200) for role in ('minio','backend','frontend')},
            backupCapacity={path: 300*1024**3 for path in ('repository','operations','staging','archive')},
            plan=dict(state='READY',parentChainRef='parent',baseFullRef='full',planDigest='a'*64))

    def test_ready_plan_uses_current_parent_without_new_full(self):
        validate_runtime(self.value, 'submit')
        self.assertEqual(plan_for_gate(self.value, 'I1', 'submit'), self.value['plan'])

    def test_unhealthy_or_non_main_source_rejected(self):
        for key in ('servicesRunning','mainSourceMatchesTarget'):
            with self.subTest(key=key):
                value=copy.deepcopy(self.value);value[key]=False
                with self.assertRaises(ValueError):validate_runtime(value,'submit')
        value=copy.deepcopy(self.value);value['health']['backend']['ready']=False
        with self.assertRaises(ValueError):validate_runtime(value,'preview')

    def test_busy_unknown_or_reserved_source_rejected(self):
        for change in ({'sourceIdle':False},{'workerPids':[17]},{'activeReservation':True}):
            with self.subTest(change=change):
                value=copy.deepcopy(self.value);value.update(change)
                with self.assertRaises(ValueError):validate_runtime(value,'submit')

    def test_verify_can_observe_worker_but_does_not_prove_source_restored(self):
        self.value.update(sourceIdle=False,workerPids=[17])
        validate_runtime(self.value,'verify')

    def test_real_backup_paths_all_require_capacity(self):
        for path in self.value['backupCapacity']:
            value=copy.deepcopy(self.value);value['backupCapacity'][path]=10
            with self.assertRaises(ValueError):validate_runtime(value,'submit')

    def test_capacity_roles_are_required_even_when_paths_share_a_filesystem(self):
        self.value['backupCapacity']['other']=self.value['backupCapacity'].pop('archive')
        with self.assertRaises(ValueError):validate_runtime(self.value,'submit')

    def test_full_and_incremental_plan_types_cannot_be_substituted(self):
        with self.assertRaises(ValueError):plan_for_gate(self.value,'FULL','submit')
        self.value['plan']['state']='BASELINE_REQUIRED'
        self.value['plan']['parentChainRef']=None;self.value['plan']['baseFullRef']=None
        with self.assertRaises(ValueError):plan_for_gate(self.value,'I1','submit')
        self.assertEqual(plan_for_gate(self.value,'FULL','preview')['state'],'BASELINE_REQUIRED')

    def test_verify_keeps_original_plan_after_current_plan_advances(self):
        original=dict(state='READY',parentChainRef='previous',baseFullRef='full',planDigest='b'*64)
        self.assertEqual(plan_for_gate(self.value,'I1','verify',original),original)
        with self.assertRaises(ValueError):plan_for_gate(self.value,'I1','verify')


if __name__ == '__main__':unittest.main()
