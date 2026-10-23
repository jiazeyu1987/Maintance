"""Exact zero-scope policy tests; no target database or deployment is contacted."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import intruoyi_runtime_agent as agent
from intruoyi_runtime import RuntimeBlocked, LEGACY_FORM_SWITCH_MIGRATION, LEGACY_FORM_SWITCH_SHA256, validate_migration_handler

COLUMNS={
 'mes_pro_route_flow_process_batch_record':'deleted form_template_id batch_record_report_id',
 'mes_pro_route_version':'id deleted route_snapshot_json',
 'bpm_form_template_version':'deleted batch_record_report_id',
 'mes_pro_batch_record_report':'report_id deleted',
 'jimu_report':'id del_flag',
}

class LegacyFormScopeTests(unittest.TestCase):
 def setUp(self):
  self.item=dict(migrationId=LEGACY_FORM_SWITCH_MIGRATION,sha256=LEGACY_FORM_SWITCH_SHA256,type='data',file='old.sql')
  self.manifest=dict(releaseTag='2026-10-23-01-00-00',migrations=[self.item])
 def target(self,counts,events,missing=None):
  def sql(profile,text):
   events.append(text)
   if text=='SHOW TABLES;':return '\n'.join(COLUMNS)
   if text.startswith('DESCRIBE '):
    name=text.split('`')[1]
    return '\n'.join(column+'\tany' for column in COLUMNS[name].split() if (name,column)!=missing)
   if text.startswith('SET SESSION TRANSACTION READ ONLY;'):
    self.assertIn('START TRANSACTION READ ONLY;',text)
    self.assertTrue(text.endswith('ROLLBACK;'))
    return '\n'.join(name+'\t'+str(value) for name,value in zip(('binding','snapshot','jimu'),counts))
   return ''
  return sql
 def test_exact_migration_checksum_is_required(self):
  with self.assertRaisesRegex(RuntimeBlocked,'bytes changed'):
   validate_migration_handler(dict(self.item,sha256='0'*64))
 def test_each_nonzero_scope_refuses_before_original_sql_or_ledger(self):
  for counts in ((1,0,0),(0,1,0),(0,0,1)):
   with self.subTest(counts=counts),tempfile.TemporaryDirectory() as folder:
    root=Path(folder);(root/'old.sql').write_text('ORIGINAL SQL','utf-8');events=[]
    with patch.object(agent,'require_migration_maintenance'),patch.object(agent,'file_sha',return_value=LEGACY_FORM_SWITCH_SHA256), \
      patch.object(agent.remote,'sql',side_effect=self.target(counts,events)),patch.object(agent,'run_target_preflight') as preflight:
     with self.assertRaisesRegex(RuntimeBlocked,'Known legacy conversion requires reviewed successor'):
      agent.apply_migration_plan({'environment':'test'},root,self.manifest,[dict(migrationId=LEGACY_FORM_SWITCH_MIGRATION,action='APPLY',targetPreflight={})],recovery={'verified':True})
    self.assertFalse(any('INSERT INTO infra_release_migration' in text or text=='ORIGINAL SQL' for text in events))
    preflight.assert_not_called()
    evidence=json.loads((root/'legacy-form-switch-scope.private.json').read_text())
    self.assertEqual(evidence['counts'],dict(zip(('binding','snapshot','jimu'),counts)))
 def test_missing_column_is_a_failure_not_a_zero(self):
  with tempfile.TemporaryDirectory() as folder,patch.object(agent,'require_migration_maintenance'), \
    patch.object(agent.remote,'sql',side_effect=self.target((0,0,0),[],('bpm_form_template_version','batch_record_report_id'))):
   with self.assertRaisesRegex(RuntimeBlocked,'prerequisite columns missing'):
    agent.require_legacy_form_switch_zero_scope({'environment':'test'},Path(folder),self.manifest,self.item,{})
   self.assertFalse((Path(folder)/'legacy-form-switch-scope.private.json').exists())
 def test_all_three_actual_zeros_execute_original_sql_and_real_ledger(self):
  with tempfile.TemporaryDirectory() as folder:
   root=Path(folder);(root/'old.sql').write_text('ORIGINAL SQL','utf-8');events=[]
   with patch.object(agent,'require_migration_maintenance'),patch.object(agent,'file_sha',return_value=LEGACY_FORM_SWITCH_SHA256), \
     patch.object(agent.remote,'sql',side_effect=self.target((0,0,0),events)),patch.object(agent,'run_target_preflight'):
    agent.apply_migration_plan({'environment':'test'},root,self.manifest,[dict(migrationId=LEGACY_FORM_SWITCH_MIGRATION,action='APPLY',targetPreflight={})],recovery={'verified':True})
   index=events.index('ORIGINAL SQL')
   self.assertTrue('INSERT INTO infra_release_migration' in events[index-1])
   self.assertTrue("status='APPLIED'" in events[index+1])
   self.assertTrue(any(text.startswith('SET SESSION TRANSACTION READ ONLY;') for text in events[:index-1]))
 def test_scope_query_cannot_run_without_maintenance_and_snapshot(self):
  with patch.object(agent.remote,'sql') as sql:
   with self.assertRaisesRegex(RuntimeBlocked,'Completed recovery record'):
    agent.require_legacy_form_switch_zero_scope({},Path('.'),self.manifest,self.item,None)
   sql.assert_not_called()

 def test_application_scope_exclusion_never_checks_or_executes_old_conversion(self):
  with patch.object(agent,'require_legacy_form_switch_zero_scope') as gate,patch.object(agent.remote,'sql') as sql:
   agent.apply_migration_plan({'environment':'test'},Path('.'),dict(self.manifest,publishScope='application'),
                             [dict(migrationId=LEGACY_FORM_SWITCH_MIGRATION,action='SKIP_SCOPE_EXCLUDED')])
  gate.assert_not_called()
  sql.assert_not_called()

if __name__=='__main__':unittest.main()
