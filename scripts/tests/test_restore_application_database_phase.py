"""Exercise the database phase gate from the actual SAFE generated source."""
import ast
import sys
from pathlib import Path
from types import SimpleNamespace

import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'ops/backup_engine'))
import build_variants


def require(condition, message):
    if not condition:
        raise ValueError(message)


def gate():
    payload = build_variants.safe_fixes(build_variants.standard_sources()[0])
    sql_tree = ast.parse(payload['formal/formal_sql_restore.py'])
    functions = [n for n in sql_tree.body if isinstance(n, ast.FunctionDef)
                 and n.name in ('database_state', 'import_database_state')]
    sql = {'require': require, 'SYSTEM_DATABASES': {'mysql', 'sys', 'information_schema', 'performance_schema'}}
    exec(compile(ast.Module(body=functions, type_ignores=[]), '<packaged-sql>', 'exec'), sql)
    runtime = ast.parse(payload['common/recovery_minimal_runtime.py'])
    cls = next(n for n in runtime.body if isinstance(n, ast.ClassDef) and n.name == 'MinimalData')
    bound = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == 'bound')
    start = next(i for i, n in enumerate(bound.body) if isinstance(n, ast.Assign)
                 and any(isinstance(t, ast.Name) and t.id == 'sql' for t in n.targets))
    bound.body = bound.body[start:]
    namespace = {'require': require}
    exec(compile(ast.Module(body=[bound], type_ignores=[]), '<packaged-phase>', 'exec'), namespace)
    def invoke(running=False, transactions=0, uuid='target', readonly=0, scheduler='OFF', extra=False, importing=False):
        def query(statement):
            if statement == 'SHOW DATABASES;':
                return '\n'.join(sorted(sql['SYSTEM_DATABASES'] | {'app'} | ({'unexpected'} if extra else set())))+'\n'
            fields = [uuid, str(readonly), '0']
            if 'innodb_trx' in statement:
                fields.append(str(transactions))
            return '\t'.join(fields+[scheduler])+'\n'
        obj = SimpleNamespace(modules={'formal_sql_restore': SimpleNamespace(**sql)},
                              mysql=SimpleNamespace(query=query), db_target={'databaseUuid':'target','database':'app'},
                              running_applications={'backend'} if running else set())
        namespace['bound'](obj, importing=importing)
    return invoke


class PhaseTests(unittest.TestCase):
    def test_application_transactions(self):
        gate()(running=True, transactions=1)

    def test_quiescent_transactions(self):
        with self.assertRaisesRegex(ValueError, "FORMAL_SQL_DATABASE_CHANGED"):
            gate()(transactions=1)

    def test_identity_mode_and_scope(self):
        invoke = gate()
        for change in [{"uuid":"other"}, {"readonly":1}, {"scheduler":"ON"}, {"extra":True}]:
            with self.subTest(change=change), self.assertRaisesRegex(ValueError, "FORMAL_SQL_"):
                invoke(running=True, transactions=1, **change)

    def test_import_transactions(self):
        gate()(importing=True, transactions=1)

if __name__ == "__main__":
    unittest.main()
