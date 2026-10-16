"""Importer adapter contracts with real local children, not SQL restore proof."""
import hashlib
from pathlib import Path
import subprocess
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'ops' / 'recovery'))
from recovery_data import NativeData
from recovery_engine import Budget, RecoveryError, check_pin, load, pin


class LocalStreamContract:
    """Exercise the subprocess API used by formal_sql_restore.stream_import."""
    def __init__(self, exit_code=0, *, timeout=False, unavailable=False, unknown_exit=False):
        self.subprocess = subprocess
        self.exit_code = exit_code
        self.timeout = timeout
        self.unavailable = unavailable
        self.process = None
        self.unknown_exit = unknown_exit

    def stream_import(self, mysql, path, checksum, seconds, *, database, guard):
        assert database == 'import_contract'
        guard()
        command = [sys.executable, '-B', '-c',
            'import hashlib,sys,time; '
            'raw=sys.stdin.buffer.read(); '
            'assert hashlib.sha256(raw).hexdigest()==sys.argv[1]; '
            'time.sleep(float(sys.argv[3])); '
            'raise SystemExit(int(sys.argv[2]))',
            checksum, str(self.exit_code), '10' if self.timeout else '0']
        if self.unavailable:
            command = [str(path.parent / 'missing-importer-executable')]
        process = self.subprocess.Popen(command, stdin=self.subprocess.PIPE,
            stdout=self.subprocess.DEVNULL, stderr=self.subprocess.DEVNULL)
        self.process = process
        try:
            process.communicate(path.read_bytes(), timeout=.01 if self.timeout else seconds)
        except self.subprocess.TimeoutExpired:
            process.kill()
            process.communicate(timeout=5)
            raise RecoveryError('LOCAL_IMPORT_TIMEOUT')
        if process.returncode:
            raise RecoveryError('FORMAL_SQL_IMPORT_FAILED', unknown=self.unknown_exit)


def importer(tmp_path, module):
    native = NativeData.__new__(NativeData)
    native.modules = {'formal_sql_restore': module}
    native.root = tmp_path
    native.config = {'database': 'import_contract'}
    native.mysql = object()
    native.budget = Budget(15000)
    native.original_pins = []
    native.last_exit = None
    native.mutation_dispatched = False
    guarded = []
    native.bound = lambda **kwargs: guarded.append(kwargs)
    native.guard = lambda: native.budget.remaining()
    sql = tmp_path / 'expanded.sql'
    sql.write_bytes(b'CREATE TABLE contract (id INT);\n')
    return native, sql, guarded


@pytest.mark.parametrize('exit_code', [0, 7])
def test_import_sql_preserves_pipe_constants_exit_evidence_and_module(tmp_path, exit_code):
    module = LocalStreamContract(exit_code)
    native, sql, guarded = importer(tmp_path, module)
    checksum = hashlib.sha256(sql.read_bytes()).hexdigest()
    if exit_code:
        with pytest.raises(RecoveryError, match='FORMAL_SQL_IMPORT_FAILED') as failure:
            native.import_sql(sql, checksum)
        assert failure.value.unknown is False
    else:
        native.import_sql(sql, checksum)
    assert module.subprocess is subprocess
    assert module.process.returncode == native.last_exit == exit_code
    assert native.mutation_dispatched and guarded == [{'importing': True}] * (1 if exit_code else 2)
    assert len(native.original_pins) == 1
    check_pin(native.original_pins[0])
    evidence = load(tmp_path / 'importer-000.json')
    assert evidence['actualExitCode'] == exit_code
    assert evidence['state'] == ('SUCCEEDED' if exit_code == 0 else 'FAILED_RETAINED')
    assert evidence['sqlPin'] == pin(sql)
    assert evidence['startedAt'] and evidence['finishedAt']


def test_transport_exit_without_remote_acknowledgement_stays_unknown(tmp_path):
    module = LocalStreamContract(1, unknown_exit=True)
    native, sql, _ = importer(tmp_path, module)
    with pytest.raises(RecoveryError, match='FORMAL_SQL_IMPORT_FAILED') as failure:
        native.import_sql(sql, hashlib.sha256(sql.read_bytes()).hexdigest())
    assert failure.value.unknown is True
    evidence = load(tmp_path/'importer-000.json')
    assert evidence['actualExitCode'] == 1 and evidence['state'] == 'TERMINAL_UNKNOWN'


def test_import_sql_timeout_preserves_unknown_and_actual_child_exit(tmp_path):
    module = LocalStreamContract(timeout=True)
    native, sql, _ = importer(tmp_path, module)
    with pytest.raises(RecoveryError, match='LOCAL_IMPORT_TIMEOUT') as failure:
        native.import_sql(sql, hashlib.sha256(sql.read_bytes()).hexdigest())
    assert failure.value.unknown is True
    assert module.subprocess is subprocess
    assert module.process.returncode == native.last_exit and native.last_exit != 0
    evidence = load(tmp_path / 'importer-000.json')
    assert evidence['actualExitCode'] == native.last_exit
    assert evidence['state'] == 'TERMINAL_UNKNOWN'
    check_pin(native.original_pins[0])


def test_import_sql_launch_error_restores_module_and_retains_intent(tmp_path):
    module = LocalStreamContract(unavailable=True)
    native, sql, _ = importer(tmp_path, module)
    with pytest.raises(OSError):
        native.import_sql(sql, hashlib.sha256(sql.read_bytes()).hexdigest())
    assert module.subprocess is subprocess
    assert module.process is None and native.last_exit is None and native.original_pins == []
    evidence = load(tmp_path / 'importer-000.json')
    assert evidence['actualExitCode'] is None and evidence['state'] == 'TERMINAL_UNKNOWN'
    assert 'finishedAt' not in evidence
