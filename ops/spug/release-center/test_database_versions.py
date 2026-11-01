"""Focused contracts; remote success is verified separately through real Spug."""
import copy
import json
import unittest
from unittest.mock import Mock

from application_registry import ApplicationRegistry, RegistryError
from database_versions import parse_snapshot, read_database, compare_targets, public_targets, SCHEMA_VERSION
from intruoyi_executor import IntRuoyiExecutor


def raw(status='APPLIED', extra=False):
    rows = [dict(section='tables', item=dict(TABLE_NAME='sample', ENGINE='InnoDB')),
            dict(section='columns', item=dict(TABLE_NAME='sample', COLUMN_NAME='id', COLUMN_TYPE='bigint')),
            dict(section='triggers', item=dict(TRIGGER_NAME='trigger', ACTION_STATEMENT='BEGIN\nSELECT 1;\nEND')),
            dict(section='ledger', item=dict(id=1, migrationId='M1', sha256='a'*64, status=status))]
    if extra:
        rows.append(dict(section='columns', item=dict(TABLE_NAME='sample', COLUMN_NAME='name', COLUMN_TYPE='varchar(64)')))
    return '\n'.join(json.dumps(r) for r in rows)


def observation(**options):
    return dict(parse_snapshot(raw(**options)), status='ok', stable=True, algorithm=SCHEMA_VERSION,
                host='host', database='db', mysqlVersion='8.0.39', lowerCaseTableNames='1')


class DatabaseVersionTests(unittest.TestCase):
    def test_multiline_definitions_count_once_and_do_not_leave_host(self):
        result = parse_snapshot(raw())
        self.assertEqual(result['schema']['counts']['triggers'], 1)
        self.assertNotIn('SELECT 1', json.dumps(result))

    def test_applied_and_already_present_are_equivalent_without_comparing_history(self):
        targets = dict(test=observation(), prod=observation(status='SKIPPED_ALREADY_APPLIED'), backup=observation())
        self.assertTrue(all(p['status'] == 'identical' for p in compare_targets(targets)))
        targets['backup']['schema']['sha256']='different'
        self.assertFalse(compare_targets(targets)[1]['schemaEqual'])

    def test_same_count_and_migration_id_with_changed_checksum_is_different(self):
        targets={env:observation() for env in ('test','prod','backup')}
        targets['prod']['migrations']['items']['M1']['sha256']='b'*64
        pair=compare_targets(targets)[0]
        self.assertFalse(pair['migrationsEqual'])
        self.assertEqual(pair['migrationDifferenceCount'],1)

    def test_failed_or_conflicting_ledger_is_not_reported_as_consistent(self):
        targets={env:observation(status='FAILED') for env in ('test','prod','backup')}
        self.assertTrue(all(p['migrationsEqual'] is None for p in compare_targets(targets)))
        conflict=raw()+'\n'+json.dumps(dict(section='ledger',item=dict(id=2,migrationId='M1',sha256='b'*64,status='APPLIED')))
        value=parse_snapshot(conflict)
        self.assertEqual(value['migrations']['checksumConflicts'],['M1'])
        self.assertFalse(value['migrations']['healthy'])

    def test_stable_check_detects_concurrent_schema_change_using_read_only_queries(self):
        remote=Mock()
        remote.inspect.return_value=dict(Id='db',State=dict(Running=True,StartedAt='now'))
        remote.sql.side_effect=['sample','definition','db\t8.0.39\t1',raw(),raw(extra=True)]
        value=read_database(remote,dict(database='db',host='host'))
        self.assertEqual(value['status'],'changed')
        for call in remote.sql.call_args_list:
            query=call.args[1]
            self.assertTrue(query.startswith(('SHOW ','DESCRIBE ','SELECT ')))
            self.assertNotIn('UPDATE ',query)
        targets=dict(test=value,prod=observation(),backup=observation())
        self.assertIsNone(compare_targets(targets)[0]['schemaEqual'])

    def test_public_response_excludes_maps_and_bounds_differences(self):
        targets=dict(test=observation(),prod=observation(extra=True),backup=observation())
        public=public_targets(targets)
        self.assertNotIn('objects',public['test']['schema'])
        self.assertNotIn('items',public['test']['migrations'])
        pair=compare_targets(targets,limit=0)[0]
        self.assertEqual(pair['structureDifferenceCount'],1)
        self.assertEqual(pair['structureDifferences'],[])

    def test_executor_partial_failure_does_not_save_or_change_baselines(self):
        e=object.__new__(IntRuoyiExecutor)
        e.c=dict(applicationId='intruoyi')
        e.state=dict(environments=dict(test=dict(schemaSha256='old')))
        before=copy.deepcopy(e.state)
        e.save=Mock(side_effect=AssertionError('Read must not save'))
        e.runtime=Mock()
        def read(env,action):
            self.assertEqual(action,'read-database')
            if env=='backup':raise RuntimeError('SSH timed out')
            return observation()
        e.runtime.call.side_effect=read
        result=e.database_versions()
        self.assertEqual(result['status'],'unknown')
        self.assertEqual(result['targets']['backup']['status'],'error')
        self.assertEqual(e.state,before)
        e.save.assert_not_called()

    def test_route_is_read_only_and_scoped(self):
        registry=ApplicationRegistry(dict(defaultApplication='intruoyi',applications=[dict(
            id='intruoyi',name='IntRuoyi',status='ready',repo='repo',scope='unit',
            executorUrl='http://127.0.0.1:18112',bridgeKey='unit')]))
        self.assertEqual(registry.resolve('/applications/intruoyi/database-versions','GET')[1],'/database-versions')
        with self.assertRaises(RegistryError):
            registry.resolve('/applications/intruoyi/database-versions','POST',dict(applicationId='intruoyi'))


if __name__=='__main__':
    unittest.main()
