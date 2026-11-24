import ast
from pathlib import Path
import unittest
import subprocess
import sys
import tempfile


class SharedReadonlySqlTests(unittest.TestCase):
    def test_standalone_and_file_location_entries_without_pythonpath(self):
        module = Path(__file__).with_name('release_target_preflight_contract.py').resolve()
        with tempfile.TemporaryDirectory() as folder:
            query = Path(folder)/'sample.preflight.sql'
            query.write_text("-- release-target-preflight: migrationId=sample; allowedEnvironments=test\nSELECT 'TARGET_PREFLIGHT_PASS:sample';",encoding='utf-8')
            cli = subprocess.run([sys.executable, '-I', str(module), '--migration-id','sample','--path',str(query)],cwd=folder,capture_output=True)
            self.assertEqual(cli.returncode,0,cli.stderr.decode())
            code = "import importlib.util,sys; s=importlib.util.spec_from_file_location('intruoyi_existing_readonly_contract',sys.argv[1]); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); m.validate(m.Path(sys.argv[2]),'sample')"
            loaded = subprocess.run([sys.executable,'-I','-c',code,str(module),str(query)],cwd=folder,capture_output=True)
            self.assertEqual(loaded.returncode,0,loaded.stderr.decode())

    def test_runtime_module_uses_python36_grammar_and_no_future_annotations(self):
        source = Path(__file__).with_name('release_readonly_sql.py').read_text('utf-8')
        tree = ast.parse(source, feature_version=(3, 6))
        self.assertFalse(any(isinstance(node, ast.ImportFrom) and node.module == '__future__' for node in ast.walk(tree)))

    def test_both_callers_share_parser_and_exception_contract(self):
        from ops.release import release_readonly_sql as shared
        from ops.release import release_target_preflight_contract as preflight
        from ops.release import release_database_contract as database
        self.assertIs(preflight._executable_sql, shared._executable_sql)
        self.assertIs(database._executable_sql, shared._executable_sql)
        self.assertIs(preflight.TargetPreflightContractError, shared.ReadonlySqlError)

    def test_comment_quotes_cannot_hide_next_statement(self):
        from ops.release.release_readonly_sql import _executable_sql, FORBIDDEN_PATTERN, ReadonlySqlError
        for sql in ["SELECT 1; -- ' quoted comment\nDELETE FROM t;", "SELECT 'safe''literal'; # \"\nUPDATE t SET a=1;"]:
            self.assertIsNotNone(FORBIDDEN_PATTERN.search(_executable_sql(sql)))
        for sql in ["SELECT 'unterminated", 'SELECT 1; /*! DELETE FROM t */', 'SELECT \\x']:
            with self.assertRaises(ReadonlySqlError):
                _executable_sql(sql)
        self.assertIsNone(FORBIDDEN_PATTERN.search(_executable_sql("SELECT 'delete', 1; -- update\n")))


if __name__ == '__main__':
    unittest.main()
