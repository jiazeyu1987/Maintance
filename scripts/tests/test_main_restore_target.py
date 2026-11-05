"""Observable admission and drift failures for the registered main target path."""
from copy import deepcopy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import subprocess

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'ops/recovery'))
from recovery_engine import RecoveryError, digest, pin
import recovery_main_target as main


def identifier(char):
    return char * 64


class MainContractTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        proof = root / 'writer-proof.json'
        proof.write_text(json.dumps({'schemaVersion': 'RegisteredMainWriterEvidence/v1',
            'database': 'ruoyi-vue-pro', 'redisDatabase': 1,
            'objectBuckets': ['yudao'], 'writerContainerIds': [identifier('d')],
            'exclusiveResources': {'database': True, 'objects': True, 'redis': True}}), encoding='utf-8')
        roles = ('mysql', 'minio', 'redis', 'backend', 'frontend')
        self.rows = {}
        for index, role in enumerate(roles):
            identity = identifier('abcde'[index])
            self.rows[role] = {'Id': identity, 'Image': 'sha256:' + identifier('12345'[index]),
                'Path': '/entrypoint', 'Args': [], 'HostConfig': {'NetworkMode': 'main',
                    'Privileged': False}, 'Config': {'Env': ['APP=main'], 'Labels': {}},
                'State': {'Running': role in ('mysql', 'redis'), 'Paused': False, 'Restarting': False},
                'Mounts': [], 'NetworkSettings': {'Networks': {'main': {
                    'NetworkID': identifier('f'), 'IPAddress': '172.29.1.%s' % (index + 2),
                    'GlobalIPv6Address': '', 'Aliases': [role], 'Links': None, 'DriverOpts': None}}}}
        self.network = {'Id': identifier('f'), 'Name': 'main', 'Driver': 'bridge',
            'Internal': False, 'EnableIPv6': False, 'IPAM': {'Driver': 'default', 'Config': []},
            'Options': {}, 'Labels': {}, 'Containers': {self.rows[r]['Id']: {} for r in ('mysql', 'redis')}}
        self.target = {'targetId': 'main57', 'sourceConfigRef': 'prod57',
            'database': 'ruoyi-vue-pro', 'buckets': ['yudao'], 'redisRebuild': {'database': 1},
            'services': [{'role': r, 'id': row['Id'], 'imageId': row['Image'], 'ip':
                row['NetworkSettings']['Networks']['main']['IPAddress']} for r, row in self.rows.items()],
            'application': {'startOrder': ['backend', 'frontend']},
            'replacement': {'schemaVersion': 'RegisteredApplicationReplacement/v2',
                'databaseUuid': '11111111-1111-1111-1111-111111111111'},
            'mainApplication': {'schemaVersion': 'RegisteredMainApplication/v1',
                'serviceConfigurationDigests': {r: main.service_configuration_digest(row) for r, row in self.rows.items()},
                'networks': [main.network_configuration(self.network, [row['Id'] for row in self.rows.values()])],
                'networkAttachments': {r: main.network_attachments(row) for r, row in self.rows.items()},
                'archiveImageBindings': [{'role': role, 'versionPath': ['images', role],
                    'imageId': self.rows[role]['Image']} for role in ('backend', 'frontend')],
                'configurationPins': [],
                'writerAdmission': {'schemaVersion': 'RegisteredMainWriterCustody/v1',
                    'approvedWriterContainerIds': [identifier('d')],
                    'exclusiveResources': {'database': True, 'objects': True, 'redis': True},
                    'evidencePin': pin(proof)}}}
        version = root / 'version.json'
        version.write_text(json.dumps({'images': {r: row['Image'] for r, row in self.rows.items()}}), encoding='utf-8')
        self.material = {'versionPins': [pin(version)], 'sourceDatabaseUuid': self.target['replacement']['databaseUuid']}
        self.native = type('Native', (), {})()
        self.native.config = self.target
        self.native.material = self.material
        self.native.config_services = {r['role']: r for r in self.target['services']}
        self.native.snapshots = {}
        self.native.running_applications = set()
        self.native.storage_running = False
        self.native.inspect = lambda identity: deepcopy(next(r for r in self.rows.values() if r['Id'] == identity))
        self.native.docker = lambda args, **kwargs: json.dumps([self.network]).encode()
        self.native.db_uuid = self.target['replacement']['databaseUuid']
        self.native.guard = lambda: None

    def test_registered_main_accepts_matching_archived_program(self):
        main.validate(self.target)
        main.application_inputs(self.native)

    def test_main_requires_explicit_v2_replacement(self):
        self.target['replacement']['schemaVersion'] = 'RegisteredApplicationReplacement/v1'
        with self.assertRaisesRegex(RecoveryError, 'MAIN_TARGET_REPLACEMENT_V2_REQUIRED'):
            main.validate(self.target)

    def test_one_container_cannot_be_registered_for_two_roles(self):
        self.target['services'][4]['id'] = self.target['services'][3]['id']
        with self.assertRaisesRegex(RecoveryError, 'MAIN_SERVICE_BINDINGS_INVALID'):
            main.validate(self.target)

    def test_writer_ownership_unknown_blocks_admission(self):
        self.target['mainApplication']['writerAdmission']['exclusiveResources']['objects'] = False
        with self.assertRaisesRegex(RecoveryError, 'MAIN_WRITER_CUSTODY_REQUIRED'):
            main.validate(self.target)

    def test_writer_proof_cannot_describe_other_database(self):
        self.target['database'] = 'other'
        with self.assertRaisesRegex(RecoveryError, 'MAIN_WRITER_EVIDENCE_SCOPE_MISMATCH'):
            main.application_inputs(self.native)

    def test_archive_image_mismatch_blocks_before_reset(self):
        self.target['mainApplication']['archiveImageBindings'][0]['imageId'] = 'sha256:' + identifier('0')
        with self.assertRaisesRegex(RecoveryError, 'MAIN_ARCHIVED_IMAGE_MISMATCH'):
            main.application_inputs(self.native)

    def test_archive_must_cover_backend_and_frontend(self):
        self.target['mainApplication']['archiveImageBindings'].pop()
        with self.assertRaisesRegex(RecoveryError, 'MAIN_ARCHIVED_IMAGES_INCOMPLETE'):
            main.validate(self.target)

    def test_same_source_database_is_explicit_main_only(self):
        main.database_identity(self.native)
        self.target.pop('mainApplication')
        with self.assertRaisesRegex(RecoveryError, 'SOURCE_DATABASE_TARGET_REJECTED'):
            main.database_identity(self.native)

    def test_main_mysql_password_only_flows_over_stdin(self):
        seen = []
        self.native.policy = {'environmentMysqlClientPath': '/usr/bin/mysql'}
        self.native.secret = lambda *args: 'private-password-value'
        self.native.db_container = self.native.config_services['mysql']['id']
        self.native.docker = lambda args, **kwargs: seen.append((args, kwargs)) or b'row\n'
        self.assertEqual(b'row\n', main.mysql_query(self.native, 'SELECT 1;'))
        args, options = seen[0]
        self.assertNotIn('private-password-value', repr(args))
        self.assertNotIn('/run/recovery/mysql-client.cnf', repr(args))
        self.assertIn('--no-defaults', args)
        self.assertIn('IFS= read -r MYSQL_PWD', repr(args))
        self.assertEqual(b'private-password-value\n', options['input_bytes'])

    def test_registered_main_can_readback_its_bound_source_object_endpoint(self):
        endpoint = 'http://' + self.native.config_services['minio']['ip'] + ':9000'
        main.object_endpoint(self.native, endpoint)
        with self.assertRaisesRegex(RecoveryError, 'MAIN_OBJECT_ENDPOINT_CHANGED'):
            main.object_endpoint(self.native, 'http://other:9000')

    def test_physical_bind_admission_uses_registered_storage_verifier(self):
        self.native.policy = {'minioDataMount': '/data'}
        row = self.rows['minio']
        row['Mounts'] = [{'Destination': '/data', 'Type': 'bind', 'RW': True, 'Source': '/local/data/minio'}]
        with patch('recovery_replace.verify_services') as verify:
            self.assertEqual(row['Mounts'][0], main.physical_mount(self.native, row))
        verify.assert_called_once_with(self.native, self.target['replacement'])

    def test_data_client_ip_must_match_registered_attachment(self):
        self.target['services'][1]['ip'] = '172.29.1.250'
        with self.assertRaisesRegex(RecoveryError, 'MAIN_DATA_ENDPOINT_UNBOUND'):
            main.validate(self.target)

    def test_main_schema_mutation_reuses_stdin_transport(self):
        seen = []
        class Original:
            def docker(self, args, **kwargs):
                seen.append((args, kwargs)); return b''
        obj = main.guarded_type(Original)()
        obj.__dict__.update(self.native.__dict__)
        obj.__dict__.pop('docker')
        obj.policy = {'environmentMysqlClientPath': '/usr/bin/mysql'}
        obj.db_container = self.native.config_services['mysql']['id']
        obj.secret = lambda *args: 'private-password-value'
        obj.docker(['exec', obj.db_container, '/usr/bin/mysql',
            '--defaults-extra-file=/run/recovery/mysql-client.cnf', '--batch', '--skip-column-names',
            '-e', 'ALTER DATABASE `ruoyi-vue-pro` DEFAULT CHARACTER SET utf8mb4;'], mutation=True)
        args, options = seen[0]
        self.assertNotIn('/run/recovery/mysql-client.cnf', repr(args))
        self.assertNotIn('private-password-value', repr(args))
        self.assertEqual(b'private-password-value\n', options['input_bytes'])
        self.assertIs(options['mutation'], True)

    def test_main_never_adopts_unregistered_database_identity(self):
        self.native.db_uuid = '22222222-2222-2222-2222-222222222222'
        with self.assertRaisesRegex(RecoveryError, 'MAIN_DATABASE_IDENTITY_CHANGED'):
            main.database_identity(self.native)

    def test_main_preserves_nonisolated_registered_network(self):
        main.verify_runtime(self.native)

    def test_unregistered_network_member_blocks(self):
        self.network['Containers'][identifier('0')] = {}
        with self.assertRaisesRegex(RecoveryError, 'MAIN_NETWORK_MEMBERS_CHANGED'):
            main.verify_runtime(self.native)

    def test_network_route_drift_blocks(self):
        self.network['Options']['com.docker.network.bridge.enable_icc'] = 'false'
        with self.assertRaisesRegex(RecoveryError, 'MAIN_NETWORK_CONFIGURATION_CHANGED'):
            main.verify_runtime(self.native)

    def test_host_network_frontend_has_no_fake_bridge_requirement(self):
        row = self.rows['frontend']
        row['HostConfig']['NetworkMode'] = 'host'
        row['NetworkSettings']['Networks'] = {'host': {'NetworkID': identifier('9'),
            'IPAddress': '', 'GlobalIPv6Address': '', 'Aliases': None, 'Links': None, 'DriverOpts': None}}
        value = self.target['mainApplication']
        value['serviceConfigurationDigests']['frontend'] = main.service_configuration_digest(row)
        value['networkAttachments']['frontend'] = main.network_attachments(row)
        value['networks'][0]['memberContainerIds'].remove(row['Id'])
        host = {'Id': identifier('9'), 'Name': 'host', 'Driver': 'host', 'Internal': False,
            'EnableIPv6': False, 'IPAM': {}, 'Options': {}, 'Labels': {}, 'Containers': {identifier('8'): {}}}
        value['networks'].append(main.network_configuration(host, [row['Id']]))
        self.native.docker = lambda args, **kwargs: json.dumps([
            host if args[-1] == identifier('9') else self.network]).encode()
        main.verify_runtime(self.native)

    def test_bridge_can_preserve_explicit_ambient_member(self):
        self.network['Containers'][identifier('8')] = {}
        self.target['mainApplication']['networks'][0]['memberContainerIds'].append(identifier('8'))
        main.verify_runtime(self.native)
        self.network['Containers'].pop(identifier('8'))
        with self.assertRaisesRegex(RecoveryError, 'MAIN_NETWORK_MEMBERS_CHANGED'):
            main.verify_runtime(self.native)

    def test_registered_attachment_drift_blocks(self):
        self.rows['frontend']['NetworkSettings']['Networks']['main']['NetworkID'] = identifier('0')
        with self.assertRaisesRegex(RecoveryError, 'MAIN_SERVICE_NETWORK_CHANGED'):
            main.verify_runtime(self.native)

    def test_stopped_fixed_ip_attachment_remains_bound(self):
        item = self.rows['minio']['NetworkSettings']['Networks']['main']
        item['IPAMConfig'] = {'IPv4Address': item['IPAddress']}
        item['IPAddress'] = ''
        main.verify_runtime(self.native)

    def dynamic_attachment(self, role='frontend'):
        row = self.rows[role]
        fixed = row['NetworkSettings']['Networks']['main']
        fixed['IPAMConfig'] = {'IPv4Address': fixed['IPAddress']}
        dynamic = {'NetworkID': identifier('7'), 'IPAddress': '172.17.0.2',
            'GlobalIPv6Address': '', 'IPAMConfig': None, 'Aliases': None,
            'Links': None, 'DriverOpts': None}
        row['NetworkSettings']['Networks']['bridge'] = dynamic
        network = {'Id': identifier('7'), 'Name': 'bridge', 'Driver': 'bridge',
            'Internal': False, 'EnableIPv6': False,
            'IPAM': {'Driver': 'default', 'Config': [{'Subnet': '172.17.0.0/16'}]},
            'Options': {}, 'Labels': {}, 'Containers': {}}
        value = self.target['mainApplication']
        value['networkAttachments'][role] = main.network_attachments(row)
        value['networks'].append(main.network_configuration(network, [row['Id']]))
        self.native.docker = lambda args, **kwargs: json.dumps([
            network if args[-1] == identifier('7') else self.network]).encode()
        return row, dynamic, network

    def test_dynamic_attachment_empty_when_application_stopped(self):
        _, dynamic, _ = self.dynamic_attachment()
        dynamic['IPAddress'] = ''
        main.verify_runtime(self.native)

    def test_dynamic_attachment_new_running_allocation_requires_network_proof(self):
        row, dynamic, network = self.dynamic_attachment()
        row['State']['Running'] = True
        self.native.running_applications.add('frontend')
        self.network['Containers'][row['Id']] = {}
        dynamic['IPAddress'] = '172.17.0.9'
        network['Containers'][row['Id']] = {'IPv4Address': '172.17.0.9/16', 'IPv6Address': ''}
        main.verify_runtime(self.native)

    def test_dynamic_attachment_published_loopback_endpoint_stays_bound(self):
        row, dynamic, _ = self.dynamic_attachment()
        self.native.config_services['frontend']['ip'] = '127.0.0.1'
        row['HostConfig']['PortBindings'] = {'80/tcp': [{'HostIp': '', 'HostPort': '38081'}]}
        self.target['mainApplication']['serviceConfigurationDigests']['frontend'] = main.service_configuration_digest(row)
        dynamic['IPAddress'] = ''
        main.verify_runtime(self.native)

    def test_dynamic_attachment_unproven_running_allocation_rejected(self):
        row, dynamic, network = self.dynamic_attachment()
        row['State']['Running'] = True
        self.native.running_applications.add('frontend')
        self.network['Containers'][row['Id']] = {}
        dynamic['IPAddress'] = '172.17.0.9'
        network['Containers'][row['Id']] = {'IPv4Address': '172.17.0.8/16', 'IPv6Address': ''}
        with self.assertRaisesRegex(RecoveryError, 'MAIN_SERVICE_NETWORK_CHANGED'):
            main.verify_runtime(self.native)

    def test_dynamic_attachment_data_service_is_never_relaxed(self):
        _, dynamic, _ = self.dynamic_attachment('minio')
        dynamic['IPAddress'] = ''
        with self.assertRaisesRegex(RecoveryError, 'MAIN_SERVICE_NETWORK_CHANGED'):
            main.verify_runtime(self.native)

    def test_dynamic_attachment_registered_endpoint_is_never_relaxed(self):
        _, dynamic, _ = self.dynamic_attachment()
        self.native.config_services['frontend']['ip'] = '172.17.0.2'
        dynamic['IPAddress'] = ''
        with self.assertRaisesRegex(RecoveryError, 'MAIN_SERVICE_NETWORK_CHANGED'):
            main.verify_runtime(self.native)

    def test_dynamic_attachment_static_allocation_drift_rejected(self):
        _, dynamic, _ = self.dynamic_attachment()
        dynamic['IPAMConfig'] = {'IPv4Address': '172.17.0.9'}
        dynamic['IPAddress'] = ''
        with self.assertRaisesRegex(RecoveryError, 'MAIN_SERVICE_NETWORK_CHANGED'):
            main.verify_runtime(self.native)

    def test_dynamic_attachment_stopped_nonempty_drift_rejected(self):
        _, dynamic, _ = self.dynamic_attachment()
        dynamic['IPAddress'] = '172.17.0.9'
        with self.assertRaisesRegex(RecoveryError, 'MAIN_SERVICE_NETWORK_CHANGED'):
            main.verify_runtime(self.native)

    def test_dynamic_attachment_alias_drift_rejected(self):
        _, dynamic, _ = self.dynamic_attachment()
        dynamic['IPAddress'] = ''
        dynamic['Aliases'] = ['unregistered']
        with self.assertRaisesRegex(RecoveryError, 'MAIN_SERVICE_NETWORK_CHANGED'):
            main.verify_runtime(self.native)

    def test_dynamic_attachment_fixed_business_endpoint_drift_rejected(self):
        row, dynamic, _ = self.dynamic_attachment()
        dynamic['IPAddress'] = ''
        row['NetworkSettings']['Networks']['main']['IPAMConfig']['IPv4Address'] = '172.29.1.250'
        row['NetworkSettings']['Networks']['main']['IPAddress'] = ''
        with self.assertRaisesRegex(RecoveryError, 'MAIN_SERVICE_NETWORK_CHANGED'):
            main.verify_runtime(self.native)

    def test_dynamic_attachment_without_another_static_endpoint_rejected(self):
        row, dynamic, _ = self.dynamic_attachment()
        dynamic['IPAddress'] = ''
        row['NetworkSettings']['Networks']['main'].pop('IPAMConfig')
        with self.assertRaisesRegex(RecoveryError, 'MAIN_SERVICE_NETWORK_CHANGED'):
            main.verify_runtime(self.native)

    def test_capture_builds_same_explicit_contract(self):
        original = self.target['mainApplication']
        captured = main.capture_main_application(self.target, self.rows, [self.network],
            original['archiveImageBindings'], [], original['writerAdmission']['evidencePin'])
        self.assertEqual(original, captured)

    def test_program_configuration_drift_blocks(self):
        self.rows['backend']['Config']['Env'] = ['APP=other']
        with self.assertRaisesRegex(RecoveryError, 'MAIN_SERVICE_CONFIGURATION_CHANGED'):
            main.verify_runtime(self.native)

    def test_unexpected_running_writer_blocks_during_replay(self):
        self.rows['backend']['State']['Running'] = True
        with self.assertRaisesRegex(RecoveryError, 'MAIN_SERVICE_RUNNING_STATE_CHANGED'):
            main.verify_runtime(self.native)

    def test_archived_config_file_drift_blocks(self):
        p = Path(self.temp.name) / 'application.yml'
        p.write_bytes(b'original')
        self.rows['backend']['Mounts'] = [{'Type': 'bind', 'RW': False, 'Source': str(p), 'Destination': '/app.yml'}]
        self.target['mainApplication']['configurationPins'] = [pin(p)]
        main.application_inputs(self.native)
        p.write_bytes(b'changed')
        with self.assertRaises(RecoveryError):
            main.application_inputs(self.native)

    def test_unpinned_readonly_application_input_blocks(self):
        self.rows['backend']['Mounts'] = [{'Type': 'bind', 'RW': False, 'Source': '/unknown/app.yml', 'Destination': '/app.yml'}]
        with self.assertRaisesRegex(RecoveryError, 'MAIN_CONFIGURATION_MOUNT_UNPINNED'):
            main.application_inputs(self.native)

    def test_factory_preserves_ordinary_isolated_behavior(self):
        class Original:
            def bound(self, **kwargs): return 'isolated-bound'
            def fresh_target(self): return 'isolated-fresh'
            def application_inputs(self): return 'isolated-inputs'
        ordinary = main.guarded_type(Original)()
        ordinary.config = {}
        self.assertEqual('isolated-bound', ordinary.bound())
        self.assertEqual('isolated-fresh', ordinary.fresh_target())
        self.assertEqual('isolated-inputs', ordinary.application_inputs())

    def test_every_main_bound_rechecks_storage_before_sql_state(self):
        calls = []
        class Original:
            def guard(self): calls.append('archive')
        obj = main.guarded_type(Original)()
        obj.__dict__.update(self.native.__dict__)
        obj.__dict__.pop('guard')
        obj.mysql = object(); obj.db_target = {}
        obj.modules = {'formal_sql_restore': type('SQL', (), {
            'database_state': staticmethod(lambda *args: calls.append('sql')),
            'import_database_state': staticmethod(lambda *args: calls.append('import'))})}
        with patch('recovery_replace.verify_services', side_effect=lambda *a: calls.append('storage')):
            obj.bound(importing=True)
            obj.bound()
        self.assertEqual(['archive', 'storage', 'import', 'archive', 'storage', 'sql'], calls)


class SafePackageIntegrationTests(unittest.TestCase):
    def test_authenticated_safe_package_imports_main_contract_and_retains_readback(self):
        # Exercise the actual authenticated patch contexts and a fresh process:
        # the working-tree lightweight recovery_engine must not leak into it.
        sys.path.insert(0, str(ROOT / 'ops/backup_engine'))
        from build_variants import standard_sources, safe_fixes
        payload, _ = standard_sources()
        payload = safe_fixes(payload)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name, raw in payload.items():
                destination = root / name
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(raw)
            script = '''import inspect, sys
from pathlib import Path
root=Path(sys.argv[1])
sys.path[:0]=[str(root/'common'),str(root/'formal'),str(root/'control')]
import recovery_minimal_runtime as runtime
from recovery_data import NativeData
import formal_sql_restore as sql
assert runtime.MinimalData.supports_registered_main_targets is True
assert runtime.MinimalData.full_database is NativeData.full_database
assert runtime.MinimalData.incremental_database is NativeData.incremental_database
assert runtime.MinimalData.consistency is NativeData.consistency
assert 'compare_indexed_restore(' in inspect.getsource(runtime.MinimalData.physical_object_chain)
assert 'wait_healthy' in inspect.getsource(runtime.MinimalData.__mro__[1].start_application)
mysql=sql.IsolatedTargetMySql('a'*64,'stdin-only-secret',timeout=5)
command=mysql._command('mysql',['-uroot','ruoyi-vue-pro'])
assert 'stdin-only-secret' not in repr(command)
assert '/run/recovery/mysql-client.cnf' not in repr(command)
assert 'IFS= read -r MYSQL_PWD; export MYSQL_PWD;' in repr(command)
assert '--no-defaults' in command
stream=inspect.getsource(sql.stream_import)
assert 'mysql._password' in stream and 'process.stdin.write(raw)' in stream
assert 'checksum.hexdigest() == expected_sha' in stream
from recovery_engine import pin,check_pin,RecoveryError
p=root/'immutable.txt';p.write_bytes(b'original');reference=pin(p);p.write_bytes(b'modified')
try: check_pin(reference,content=False)
except RecoveryError: pass
else: raise AssertionError('safe archive integrity disabled')
'''
            result = subprocess.run([sys.executable, '-X', 'utf8', '-c', script, str(root)],
                capture_output=True, text=True, encoding='utf-8', check=False)
            self.assertEqual(0, result.returncode, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
