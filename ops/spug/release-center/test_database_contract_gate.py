"""Current application requirements are independent of migration ledger status."""
import hashlib
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch, Mock

from ops.release import release_database_contract as contract
import intruoyi_runtime_agent as agent
from intruoyi_runtime import package_identity, Runtime


class DatabaseContractTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.folder = self.root / 'sql/mysql/database-contracts'
        self.folder.mkdir(parents=True)
        self.catalog = {'schemaVersion': 'ApplicationDatabaseContract/v1',
                        'contracts': [{'id': 'rule-key', 'file': 'rule-key.sql'}]}
        self.query = "SELECT CASE WHEN COUNT(*)=1 THEN 'DATABASE_CONTRACT_PASS:rule-key' ELSE 'BLOCKED:rule-key' END FROM rules WHERE value='PATROL';"
        self.write()

    def write(self):
        (self.folder/'catalog.json').write_text(json.dumps(self.catalog), encoding='utf-8')
        (self.folder/'rule-key.sql').write_text(self.query, encoding='utf-8')

    def package(self):
        descriptor, artifacts = contract.collect(self.root)
        return {'databaseContract': descriptor, 'files': [
            {'name': name, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
            for name, path in artifacts.items()]}

    def test_actual_database_drift_blocks_even_without_pending_migrations(self):
        manifest = self.package()
        manifest['migrations'] = []
        db = sqlite3.connect(':memory:')
        self.addCleanup(db.close)
        db.execute('CREATE TABLE rules(value TEXT)')
        db.execute("INSERT INTO rules VALUES('PATROL_AM')")
        def execute(query):
            return '\n'.join(str(row[0]) for row in db.execute(query))
        with self.assertRaisesRegex(ValueError, 'rule-key'):
            contract.verify(self.root, manifest, execute)
        db.execute("INSERT INTO rules VALUES('PATROL')")
        proof = contract.verify(self.root, manifest, execute)
        self.assertEqual(proof['status'], 'PASS')
        self.assertEqual(proof['checks'], ['rule-key'])

    def test_missing_catalog_and_legacy_manifest_block_forward_release(self):
        (self.folder/'catalog.json').unlink()
        with self.assertRaises(ValueError):
            contract.collect(self.root)
        with self.assertRaises(ValueError):
            contract.verify(self.root, {'files': []}, lambda sql: '')

    def test_tampered_sql_rejected_before_database_access(self):
        manifest = self.package()
        (self.folder/'rule-key.sql').write_text("SELECT 'DATABASE_CONTRACT_PASS:rule-key';", encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'checksum'):
            contract.verify(self.root, manifest, lambda sql: self.fail('DB must not be accessed'))

    def test_catalog_and_manifest_must_describe_identical_checks(self):
        manifest = self.package()
        manifest['databaseContract']['checks'] = []
        with self.assertRaises(ValueError):
            contract.verify(self.root, manifest, lambda sql: self.fail('DB must not be accessed'))

    def test_unsafe_or_ambiguous_queries_rejected(self):
        for query in ["DELETE FROM rules;", self.query + 'SELECT 1;',
                      "SELECT GET_LOCK('x',1), 'DATABASE_CONTRACT_PASS:rule-key';",
                      "SELECT 1 INTO OUTFILE '/tmp/a';", "/*! SELECT 1 */",
                      "SELECT 'DATABASE_CONTRACT_PASS:rule-key', custom_write_function();"]:
            with self.subTest(query=query):
                self.query = query
                self.write()
                with self.assertRaises(ValueError):
                    self.package()

    def test_exact_single_pass_response_required(self):
        manifest = self.package()
        for output in ['', '1', 'DATABASE_CONTRACT_PASS:other',
                       'DATABASE_CONTRACT_PASS:rule-key\nBLOCKED',
                       'DATABASE_CONTRACT_PASS:rule-key\t1']:
            with self.subTest(output=output), self.assertRaises(ValueError):
                contract.verify(self.root, manifest, lambda sql: output)

    def test_empty_duplicate_and_traversal_catalog_rejected(self):
        for entries in [[], self.catalog['contracts'] * 2,
                        [{'id':'rule-key','file':'../rule-key.sql'}]]:
            self.catalog['contracts'] = entries
            self.write()
            with self.assertRaises(ValueError):
                self.package()

    def test_remote_current_checks_run_when_migration_plan_is_all_skipped(self):
        manifest = self.package()
        manifest.update(releaseTag='2026-11-24-00-00-00', migrations=[])
        (self.root/'manifest.json').write_text(json.dumps(manifest), encoding='utf-8')
        (self.root/'stage-verified.json').write_text(json.dumps({'manifestSha256': package_identity(manifest)}), encoding='utf-8')
        profile = {'environment': 'test'}
        with patch.object(agent.remote, 'sql', return_value='BLOCKED:rule-key') as sql:
            agent.apply_migration_plan(profile, self.root, manifest, [{'action':'SKIPPED_ALREADY_APPLIED'}])
            sql.assert_not_called()
            with self.assertRaisesRegex(agent.RuntimeBlocked, 'rule-key'):
                agent.verify_database_contract(profile, self.root, 'after-migrations', manifest)
            self.assertIn('START TRANSACTION READ ONLY', sql.call_args.args[1])

    def test_failed_opening_contract_stops_before_opening_any_writer(self):
        manifest = self.package()
        manifest['releaseTag'] = '2026-11-24-00-00-00'
        (self.root/'manifest.json').write_text(json.dumps(manifest), encoding='utf-8')
        (self.root/'stage-verified.json').write_text(json.dumps({'manifestSha256': package_identity(manifest)}), encoding='utf-8')
        with patch.object(agent, 'directory', return_value=self.root), \
             patch.object(agent.remote, 'sql', return_value='BLOCKED:rule-key'), \
             patch.object(agent, 'docker') as docker, patch.object(agent.remote, 'inspect') as inspect:
            with self.assertRaisesRegex(agent.RuntimeBlocked, 'rule-key'):
                agent.finish_reopen({'environment':'test'}, {'releaseTag':manifest['releaseTag']})
            docker.assert_not_called()
            inspect.assert_not_called()

    def test_legacy_deploy_refused_before_remote_effects(self):
        with patch.object(agent, 'preflight') as preflight:
            with self.assertRaisesRegex(Exception, 'contract'):
                agent.deploy({'environment':'test'}, {})
            preflight.assert_not_called()

    def test_actual_transport_loads_contract_without_repository_on_remote_path(self):
        runtime = Runtime({'targets': {'test': dict(host='example.invalid', python='/usr/bin/python3',
                          entryUrl='http://example.invalid', frontend='front', backend='back',
                          database='db', stagingRoot='/release')}})
        with patch('intruoyi_runtime.subprocess.run', return_value=subprocess.CompletedProcess('ssh', 0, b'{"ok":true,"result":{}}', b'')) as transport:
            runtime.call('test', 'read-versions')
        source = transport.call_args.kwargs['input']
        harness = "import sys; __name__='contract_probe'; exec(sys.stdin.buffer.read()); from ops.release.release_database_contract import collect; print(collect(__import__('pathlib').Path(sys.argv[1]))[0]['schemaVersion'])"
        result = subprocess.run([sys.executable, '-I', '-c', harness, str(self.root)], input=source,
                                capture_output=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stderr.decode('utf-8', errors='replace'))
        self.assertEqual(result.stdout.decode().strip(), contract.VERSION)

    def test_real_deploy_path_checks_after_skipped_migrations_before_candidate_start(self):
        manifest = self.package()
        manifest.update(releaseTag='2026-11-24-00-00-00', migrations=[],
                        releaseSettings={'gxpAuditMode':'DEVELOPMENT_DISABLED'},
                        images={role:{'id':'sha256:'+'a'*64} for role in ('backend','frontend')})
        (self.root/'manifest.json').write_text(json.dumps(manifest), encoding='utf-8')
        (self.root/'stage-verified.json').write_text(json.dumps({'manifestSha256':package_identity(manifest), 'files':manifest['files']}), encoding='utf-8')
        profile = dict(environment='test', backend='backend', frontend='frontend')
        mocks = {name:Mock() for name in ('preflight','check_fence','stop_writers','persist_gxp_release_mode',
                                         'terminal_snapshot_readiness','replace','docker')}
        with patch.multiple(agent, **mocks), patch.object(agent, 'directory', return_value=self.root), \
             patch.object(agent, 'observe', return_value={}), \
             patch.object(agent, 'migration_plan', return_value=[{'action':'SKIPPED_ALREADY_APPLIED'}]), \
             patch('intruoyi_recovery_agent.capture', return_value={}), \
             patch.object(agent.remote, 'inspect', return_value={'State':{'Running':False}}), \
             patch.object(agent.remote, 'run', return_value=('sha256:'+'a'*64).encode()), \
             patch.object(agent.remote, 'sql', return_value='BLOCKED:rule-key') as sql:
            with self.assertRaisesRegex(agent.RuntimeBlocked, 'after-migrations.*rule-key'):
                agent.deploy(profile, manifest)
            mocks['stop_writers'].assert_called_once()
            mocks['replace'].assert_not_called()
            mocks['docker'].assert_not_called()
            sql.assert_called_once()


if __name__ == '__main__':
    unittest.main()
