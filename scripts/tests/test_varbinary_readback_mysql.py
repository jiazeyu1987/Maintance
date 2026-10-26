"""Real MySQL typed-row checks for both generated engine payloads.

Requires Docker with mysql:8.0.39 and python:3.12-bookworm already available,
and SPUG_TEST_DEPENDENCIES pointing to the Python dependency directory.
Creates only an isolated, labelled container with ephemeral data and no ports.
"""
import collections
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time
import unittest
import uuid

ROOT = Path(__file__).resolve().parents[2]


def command(*args, input=None, timeout=120):
    result = subprocess.run(list(args), input=input, capture_output=True, timeout=timeout)
    if result.returncode:
        raise AssertionError(result.stdout.decode() + result.stderr.decode())
    return result.stdout.decode().strip()


class VarbinaryReadbackMySql(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.label = 'varbinary-readback-' + uuid.uuid4().hex
        cls.container = command('docker', 'run', '-d', '--network', 'none',
            '--label', 'spug.test=' + cls.label, '--memory', '1g',
            '--tmpfs', '/var/lib/mysql:rw,size=512m',
            '-e', 'MYSQL_ALLOW_EMPTY_PASSWORD=yes', 'mysql:8.0.39')
        cls.addClassCleanup(cls.cleanup_container)
        for _ in range(60):
            check = subprocess.run(['docker', 'exec', cls.container, 'mysql',
                '-uroot', '-NBe', 'SELECT @@port'], capture_output=True, timeout=10)
            # The image's temporary initialization server uses port 0.
            if check.returncode == 0 and check.stdout.strip() == b'3306':
                break
            state = json.loads(command('docker', 'inspect', cls.container))[0]['State']
            if not state['Running']:
                raise AssertionError('Isolated MySQL exited before readiness')
            time.sleep(1)
        else:
            raise AssertionError('Isolated MySQL readiness deadline')
        cls.sql('CREATE DATABASE typed_readback;')
        cls.workspace = tempfile.TemporaryDirectory(prefix='spug-varbinary-')
        cls.addClassCleanup(cls.workspace.cleanup)
        spec = importlib.util.spec_from_file_location('varbinary_builder',
            ROOT/'ops/backup_engine/build_variants.py')
        builder = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(builder)
        original, _ = builder.standard_sources()
        fast, _ = builder.lightweight_sources()
        for variant, payload in [('standard', builder.safe_fixes(original)), ('lightweight', fast)]:
            for name, raw in payload.items():
                path = Path(cls.workspace.name)/variant/name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(raw)

    @classmethod
    def cleanup_container(cls):
        info = json.loads(command('docker', 'inspect', cls.container))[0]
        assert info['Id'] == cls.container and info['Config']['Labels']['spug.test'] == cls.label
        command('docker', 'rm', '-f', '-v', cls.container)

    @classmethod
    def sql(cls, sql):
        return command('docker', 'exec', '-i', cls.container, 'mysql', '-uroot',
            '-N', '-B', '--binary-mode', input=sql.encode('utf-8'))

    def generated_sql(self, variant, columns):
        program = (
            "import json,sys; from formal_data_evidence import table_sql; "
            "columns=json.load(sys.stdin); print(table_sql(columns[0][0],columns))")
        deps = os.environ['SPUG_TEST_DEPENDENCIES']
        return command('docker', 'run', '--rm', '-i', '--network', 'none',
            '-v', str(Path(self.workspace.name)/variant)+':/engine:ro',
            '-v', deps+':/deps:ro', '-e', 'PYTHONPATH=/engine/formal:/engine/common:/deps',
            '-e', 'PYTHONDONTWRITEBYTECODE=1', 'python:3.12-bookworm',
            'python', '-B', '-c', program, input=json.dumps(columns).encode())

    def test_varbinary_values_preserve_bytes_nulls_and_duplicate_rows(self):
        for variant in ('standard', 'lightweight'):
            for kind, length in (('varbinary', 320), ('varbinary', 512),
                                 ('varbinary', 1024), ('blob', 1024)):
                with self.subTest(variant=variant, kind=kind, length=length):
                    values = [None, b'', b'\0', b'a', b'a\0', b'a\0\0',
                        b'a ', b'\xff\x80\0', bytes(range(256))*(length//256)+
                        bytes(range(length % 256)), b'a\0']
                    column_type = f'VARBINARY({length})' if kind == 'varbinary' else 'BLOB'
                    self.sql('USE typed_readback; DROP TABLE IF EXISTS samples; '
                        f'CREATE TABLE samples (v {column_type}); INSERT INTO samples VALUES '+
                        ','.join('(NULL)' if v is None else "(X'"+v.hex()+"')" for v in values)+';')
                    metadata = self.sql("SELECT TABLE_NAME,COLUMN_NAME,ORDINAL_POSITION,DATA_TYPE,COLUMN_TYPE "
                        "FROM information_schema.COLUMNS WHERE TABLE_SCHEMA='typed_readback' "
                        "AND TABLE_NAME='samples' ORDER BY ORDINAL_POSITION;")
                    columns = [line.split('\t')+['']*6 for line in metadata.splitlines()]
                    sql = self.generated_sql(variant, columns)
                    result = self.sql('USE typed_readback; '+sql)
                    observed = collections.Counter(line.split('\t')[2] for line in result.splitlines())
                    expected = collections.Counter(hashlib.sha256(b'row/v1:'+(
                        b'N' if v is None else b'V'+hashlib.sha256(v).hexdigest().encode())).hexdigest()
                        for v in values)
                    self.assertEqual(observed, expected)
                    self.assertEqual(sum(observed.values()), len(values))
                    self.assertEqual(len(observed), len(values)-1)

    def test_unknown_geometry_type_still_fails_closed(self):
        self.sql('USE typed_readback; DROP TABLE IF EXISTS unknown_type; '
            'CREATE TABLE unknown_type (v GEOMETRY);')
        columns = [line.split('\t')+['']*6 for line in self.sql(
            "SELECT TABLE_NAME,COLUMN_NAME,ORDINAL_POSITION,DATA_TYPE,COLUMN_TYPE "
            "FROM information_schema.COLUMNS WHERE TABLE_SCHEMA='typed_readback' "
            "AND TABLE_NAME='unknown_type';").splitlines()]
        for variant in ('standard', 'lightweight'):
            with self.subTest(variant=variant):
                with self.assertRaisesRegex(AssertionError, 'FORMAL_DATA_TYPE_UNSUPPORTED'):
                    self.generated_sql(variant, columns)


if __name__ == '__main__':
    unittest.main()
